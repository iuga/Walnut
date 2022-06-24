import typing as t

import pendulum

from walnut import Step
from walnut.errors import StepExcecutionError


class KubernetesStep(Step):
    """
    Base and Abstract Step to interact with Kubernetes. All Steps that require
    Kubernetes access should inherit from this class.
    """

    templated: t.Sequence[str] = tuple({"namespace", "context"} | set(Step.templated))

    def __init__(self, namespace: str, context: str, title: str = None):
        super().__init__(title=title)
        self.namespace = namespace
        self.context = context

    def get_client(self):
        try:
            from kubernetes import client, config

            config.load_kube_config(context=self.context)
            return client.CoreV1Api()
        except ImportError:
            raise StepExcecutionError("kubernetes client is required: pip install kubernetes")
        except Exception as err:
            raise StepExcecutionError(f"kubernetes client error: {err}")

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        return super().execute(inputs, store)


class GetSecretStep(KubernetesStep):
    """
    Downloads the kubernetes secret on the given namespace and context and stores the
    result in {kubernetes}.{secrets}.{SECRET_NAME} as a dictionary.
    """

    templated: t.Sequence[str] = tuple({"name"} | set(Step.templated))

    def __init__(self, name: str, namespace: str, context: str, title: str = None):
        super().__init__(namespace, context, title=title)
        self.name = name

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        super().execute(inputs, store)
        try:
            client = self.get_client()
            s = client.read_namespaced_secret(self.name, namespace=self.namespace)
            return {"kubernetes": {"secrets": {self.name: s.to_dict()}}}
        except Exception as err:
            raise StepExcecutionError(f"kubernetes client error: {err}")


class GetPodsStep(KubernetesStep):
    """
    Returns a dictionary containing the pods with the "get pods" information:
    NAME                             READY   STATUS      RESTARTS   AGE
    {pod_name}                       1/1     Running     0          24h

    Using the following format:
    {
        "kubernetes": {
            {namespace}: {
                "pods": [{
                    "name": {pod_name},
                    "ready": [{ready}, {count}]
                    "status": {status},
                    "restarts": {restart_count},
                    "age": {age_in_minutes}
                }]
            }
        }
    }
    """

    def execute(
        self,
        inputs: t.Dict[t.Any, t.Any],
        store: t.Dict[t.Any, t.Any],
    ) -> t.Dict[t.Any, t.Any]:
        super().execute(inputs, store)
        try:
            client = self.get_client()
            pods = client.list_namespaced_pod(namespace=self.namespace)
            items = []
            for p in pods.items:
                restarts = 0
                ready = 0
                containers = 0
                if p is not None and p.status is not None and p.status.container_statuses is not None:
                    for cs in p.status.container_statuses:
                        restarts += cs.restart_count
                        ready = ready + 1 if cs.ready else ready
                    containers = len(p.status.container_statuses)
                st = pendulum.now() - pendulum.instance(p.status.start_time)
                items.append({
                    "name": p.metadata.name,
                    "ready": [ready, containers],
                    "status": p.status.phase,
                    "restarts": restarts,
                    "age": st.minutes,
                })
            return {"kubernetes": {self.namespace: {"pods": items}}}
        except Exception as err:
            raise StepExcecutionError(f"kubernetes client error: {err}")
