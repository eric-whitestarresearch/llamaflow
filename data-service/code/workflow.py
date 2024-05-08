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


from flask import abort, request, current_app


def get_workflow_definition(bundle,name,version):
    """
    A function to get the definitin of an workflow from the database
    
    Parameters:
        bundle (Str): The bundle the action resides in
        workflow_name (Str): The name of the action
        version (Int): The version of the action
    Returns:
        Dict: A dict with the defination of the action.
        Schema:
            "namespace": String,
            "workflow_name": String,
            "version": Int,
            "workflow": Dict,
            "parameter_schema": None, to be used later
    """

    db_connection = current_app.db_connection
    
    query = {"$and": [
        {"namespace":bundle},
        {"workflow_name":name},
        {"version":version}
    ]}

    result = db_connection.find_one_by_query("workflow-engine", "workflowDefinition",query)
    if result:
        return result
    else:
        abort(406, f"Workflow {name} in bundle {bundle} with version {version} not found")
