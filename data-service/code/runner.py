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
from flask import abort, request
import re
from kubernetes import client, config, utils
import yaml
from urllib.parse import urlparse
from bson.objectid import ObjectId
from time import sleep

def get_workflow_execution(execution_id):
    """
    The function to get the information about an workflow execution. It will include the parameters the workflow should run with and if it has completed the result.

    Return schema:
    "_id": ObjectId(Str),
    "workflow_namespace": Str,
    "workflow_name": Str,
    "version": Number
    "result": Dict,
    "status": Str ("submitted","completed","running","failed"),
    "completion_time": Unix timestamp,
    "parameters": The parameters for the action, this will be a string or object, depending on the workflow

    Parameters:
        execution_id (string): A 24 character hexadecimal string with lowercase letters.

    Returns:
        Dict: A dictory with the workflow execution information.
    """
    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")

    db_connection = Database("workflow-engine", "workflowExecution")
    
    result = db_connection.find_by_id(execution_id)
    if result:
        return result
    else:
        raise(f"Workflow execution {execution_id} not found", execution_id)


    """
    A function to execute a workflow

    Parameters:
        execution_id (string): A 24 character hexadecimal string with lowercase letters.

    Returns:
        none
    """
    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")

    execution = get_workflow_execution(execution_id)
    definition = get_workflow_definition(execution["workflow_namespace"],execution["workflow_name"],execution["version"])

    entrypoint = definition['entrypoint']
    current_action = definition['workflow'][entrypoint]
    step_name = entrypoint
    workflow_complete = False
    action_executions = {}

    while not workflow_complete:
        action_executions[step_name] = single_action_execute(current_action['action_namespace'], current_action['action_name'], current_action['version'], current_action['parameters'])
         
        if current_action['on_success'] != "complete_workflow":
            next_step = current_action['on_success']
            current_action = definition['workflow'][next_step]
            step_name = next_step
        else:
            workflow_complete = True

    workflow_result = {
        "status": "success",
        "action_executions": action_executions
    }

    update_workflow_result(execution_id, workflow_result)


def result(execution_id, runner_result):
    """
    A function to capture the result of an actin execution

    Parameters:
        execution_id (string): A 24 character hexadecimal string with lowercase letters.
        runner_result (dict): A dictonary containg the result of the execution

    Returns:
        none  
    """
    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")

    db_connection = Database("workflow-engine", "runnerExecution")

    runner_result['time'] = int(time.time())

    print(runner_result)
    print("The execution id is: " + execution_id)


    query = {"_id": ObjectId(execution_id)}
    result = db_connection.collection.update_one(query, {'$set':runner_result})
    print("Insert Result: ", result.upserted_id)

def update_workflow_result(execution_id, workflow_result):
    """
    A function to capture the result of an workflow execution

    Parameters:
        execution_id (string): A 24 character hexadecimal string with lowercase letters.
        workflow_result (dict): A dictonary containg the result of the execution

    Returns:
        none  
    """

    global db_connection

    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")

    workflow_result['time'] = int(time.time())

    print(workflow_result)
    print("The execution id is: " + execution_id)


    query = {"_id": ObjectId(execution_id)}
    result = db_connection.update_one("workflow-engine", "workflowExecution", query, {'$set':workflow_result})
    return result


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
    "execution_status": Str ("submitted", "success", "failed")
    "parameters": The parameters for the action, this will be a string or object, depending on the action

    Parameters:
        execution_id (string): A 24 character hexadecimal string with lowercase letters.

    Returns:
        Dict: A dictory with the action execution information.
    """
    if not re.match('^[0-9a-f]{24}$',execution_id):
        abort(406, "Execution id must be 24 chacters hexadecimal string with lowercase letters")
    
    global db_connection
    result = db_connection.find_by_id("workflow-engine", "runnerExecution",execution_id)
    if result:
        return result
    else:
        abort(404, f"Execution {execution_id} not found")

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
    global db_connection
    
    query = {"$and": [
        {"namespace":action_namespace},
        {"action_name":action_name},
        {"version":version}
    ]}
    
    result = db_connection.find_one_by_query("workflow-engine", "actionDefinition",query)
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
        execution_status (Str): ("submitted", "success","failed")

    Returns:
        execution_id (Str): A 24 character hexadecimal string 
    """
    global db_connection

    document = {
        "action_namespace": action_namespace,
        "action_name": action_name,
        "version": version,
        "parameters": parameters,
        "job_id": job_id,
        "execution_status": "submitted"
    }
    
    execution_id = db_connection.insert_document("workflow-engine", "runnerExecution", document)

    return execution_id

def do_something():
    pass
