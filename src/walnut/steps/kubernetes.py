import typing as t

import pendulum

from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import MappingMessage, Message, SequenceMessage


class KubernetesStep(Step):
    """
    Base and Abstract Step to interact with Kubernetes. All Steps that require
    Kubernetes access should inherit from this class.
    """

    templated: t.Sequence[str] = tuple({"namespace", "context"} | set(Step.templated))

    def __init__(self, namespace: str, context: str, **kwargs):
        super().__init__(**kwargs)
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

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        raise NotImplementedError("KubernetesStep is an abstract step and it should never be called directly.")


class ReadNamespacedSecretStep(KubernetesStep):
    """
    Downloads the kubernetes secret on the given namespace and context.
    """

    templated: t.Sequence[str] = tuple({"name"} | set(Step.templated))

    def __init__(self, name: str, namespace: str, context: str, **kwargs):
        super().__init__(namespace, context, **kwargs)
        self.name = name

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        try:
            client = self.get_client()
            s = client.read_namespaced_secret(self.name, namespace=self.namespace)
            return MappingMessage(s.to_dict())
        except Exception as err:
            raise StepExcecutionError(f"error reading the secret {self.name} on namespace {self.namespace}: {err}")


class ListNamespacedPodStep(KubernetesStep):
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
    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
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
            return SequenceMessage(items)
        except Exception as err:
            raise StepExcecutionError(f"error listing the pods in the {self.namespace} namespace: {err}")


class ReadNamespacedPodLog(KubernetesStep):
    """
    ReadNamespacedPodLog reads the log of the specified Pod
    """
    templated: t.Sequence[str] = tuple({"pod_name", "container"} | set(KubernetesStep.templated))

    def __init__(self, namespace: str, context: str, pod_name: str, container: str = None, **kwargs):
        super().__init__(namespace, context, **kwargs)
        self.pod_name = pod_name
        self.container = container

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        try:
            client = self.get_client()
            r = client.read_namespaced_pod_log(
                namespace=self.namespace,
                name=self.pod_name,
                container=self.container,
                _preload_content=False,
            )
        except Exception as err:
            raise StepExcecutionError(f"error getting the log on pod {self.pod_name}/{self.container}: {err}")
        logs = [str(line) for line in r.readlines()]
        return SequenceMessage(logs)
