#     Llamaflow - A self service portal with runbook automation
#     Copyright (C) 2024  Whitestar Research LLC
#

import yaml
from kubernetes import client, config, utils

def main():
    config.load_kube_config()
    k8s_client = client.ApiClient()
    #Job YAML
    job_yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: echo-runner-from-python
  namespace: testing
spec:
  template:
    spec:
      containers:
      - name: echo-runner
        image: ericwsr/runner-echo:1
        env:
        - name: RUNNER_ARGS
          value: "I am running in a k8s job"
      restartPolicy: Never
      imagePullSecrets:
      - name: regcred
  backoffLimit: 4

"""

    job_dict=yaml.safe_load(job_yaml)
    utils.create_from_dict(k8s_client, job_dict)

if __name__ == '__main__':
    main()