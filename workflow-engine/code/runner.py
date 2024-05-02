#     Llamaflow - A self service portal with runbook automation
#     Copyright (C) 2024  Whitestar Research LLC
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.


import time
from modules.database import Database
from flask import abort, request
import re
from kubernetes import client, config, utils
import yaml
from urllib.parse import urlparse
from bson.objectid import ObjectId

def result(execution_id, runner_result):
    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")

    db_connection = Database("workflow-engine", "runnerExecution")

    runner_result['time'] = int(time.time())

    print(runner_result)
    print("The execution id is: " + execution_id)


    query = {"_id": ObjectId(execution_id)}
    result = db_connection.collection.update_one(query, {'$set':runner_result})
    print("Insert Result: ", result.upserted_id)

def get_execution(execution_id):
    """
    The function to get the information about an action execution. It will include the parameters the action should run with and if it has completed the result.

    Return schema:
    "_id": ObjectId(Str),
    "job_id": Str,
    "pod_id": Str,
    "action_name": Str,
    "standard_output": Str or None,
    "error_output": Str or None,
    "completion_time": Unix timestamp,
    "parameters": The parameters for the action, this will be a string or object, depending on the action

    Parameters:
        execution_id (string): A 24 character hexadecimal string with lowercase letters.

    Returns:
        Dict: A dictory with the action execution information.
    """
    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")

    db_connection = Database("workflow-engine", "runnerExecution")
    
    result = db_connection.find_by_id(execution_id)
    if result:
        return result
    else:
        abort(404, f"Execution {execution_id} not found")

    print(result)

def get_action_definition(action_namespace,action_name,version):
    """
    A function to get the definitin of an action from the database
    
    Parameters:
        action_namespace (Str): The namespace the action resides in
        action_name (Str): The name of the action
        version (Int): The version of the action
    Returns:
        Dict: A dict with the defination of the action.
        Schema:
            "namespace": String,
            "action_name": String,
            "version": Int,
            "container_repo": String,
            "container_name": String,
            "container_tag": String,
            "parameter_schema": None, to be used later
    """
    db_connection = Database("workflow-engine", "actionDefinition")
    query = {"$and": [
        {"namespace":action_namespace},
        {"action_name":action_name},
        {"version":version}
    ]}
    result = db_connection.find_one_by_query(query)
    if result:
        return result
    else:
        raise(f"Action in namespace: {action_namespace}, with name {action_name}, and version {version} not found")

def create_execution_record(action_namespace,action_name,version,parameters,job_id):
    """
    A function to create the inital record in the database used for a action execution

    Parameters:
        action_namespace (Str): The namespace the action resides in
        action_name (Str): The name of the action
        version (Int): The version of the action
        parameters (Object): The parameters used to run the object
        job_id (Str): The name of the kubernetes job that will run the action

    Returns:
        execution_id (Str): A 24 character hexadecimal string 
    """
    db_connection = Database("workflow-engine", "runnerExecution")
    document = {
        "action_namespace": action_namespace,
        "action_name": action_name,
        "version": version,
        "parameters": parameters,
        "job_id": job_id
    }
    
    execution_id = db_connection.insert_document(document)

    return execution_id

def submit_execution(action_namespace, action_name, version, parameters):
    """
    A function to submit an action for execution

    Parameters:
    action_namespace (Str): The namespace the action resides in
    action_name (Str): The name of the action
    parameters (Object): Contans the parameters for the action. This will vary from action to action
    """

    config.load_kube_config()
    k8s_client = client.ApiClient()

    job_id =  action_namespace + "-" + action_name + "-" + str(time.time_ns())
    action_definition = get_action_definition(action_namespace, action_name, version)
    execution_id = create_execution_record(action_namespace,action_name,version, parameters,job_id)

    #TO-DO Figure out a better way to generate the callback url
    parsed_url = urlparse(request.base_url)
    callback_base_url = parsed_url[0] + "://" + parsed_url[1] + "/api/runner/" 
                
    #This is not pretty, but better than using a heredoc with some yaml in it.
    job_dict = {
        'apiVersion': 'batch/v1',
        'kind': 'Job',
        'metadata': { 'name': job_id},
        'spec': {
            'template': {
                'spec': {
                    'containers': [{
                            'name': 'action-runner',
                            'image': f"{action_definition['container_repo']}/{action_definition['container_name']}:{action_definition['container_tag']}",
                            'env': [
                                {
                                    'name': 'RUNNER_ARGS',
                                    'value': 'I am running in a k8s job'
                                }, {
                                    'name': 'POD_ID',
                                    'valueFrom': {'fieldRef': { 'fieldPath': 'metadata.name'}}
                                }, {
                                    'name': 'JOB_ID',
                                    'value': job_id
                                }, {
                                    'name': 'EXECUTION_ID',
                                    'value': execution_id
                                }, {
                                    'name': 'POSTBACK_BASE_URL',
                                    'valueFrom': {'configMapKeyRef': {'name': 'postback-url', 'key':'url'}}
                                }
                            ]
                        }
                    ],
                    'restartPolicy': 'Never',
                    'imagePullSecrets': [
                        {'name': 'regcred'}
                    ]
                }
            },
            'backoffLimit': 0,
            'podFailurePolicy': {
                'rules': [
                    {
                        'action': 'FailJob',
                        'onExitCodes': {
                            'containerName': 'action-runner',
                            'operator': 'NotIn',
                            'values': [0]
                        }
                    }, {
                        'action': 'Ignore',
                        'onPodConditions': [
                            {'type': 'DisruptionTarget'}
                        ]
                    }
                ]
            }
        }
    }
   
    narf = utils.create_from_dict(k8s_client, job_dict, namespace="testing")
    print(narf)

def do_something():
    submit_execution("core","echo",1,"ccc")
