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

import os
import requests
from time import sleep

pod_id = os.environ['POD_ID']
job_id = os.environ['JOB_ID']
wait_seconds = os.environ["WAIT_SECONDS"]
url = os.environ["POSTBACK_HOST"] + "/" + job_id

data = {
    "job_id": job_id,
    "pod_id": pod_id,
    "execution_status": "success",
    "execution_output": "",
}

sleep(int(wait_seconds))
response = requests.post(url, json=data)

print("Status Code: ", response.status_code)
print("Data: ", data)