import typing as t

import pendulum

from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage


class KubernetesStep(Step):
    """
    Base and Abstract Step to interact with Kubernetes. All Steps that require
    Kubernetes access should inherit from this class.
    """

    templated: t.Sequence[str] = tuple({"namespace", "cluster_context"} | set(Step.templated))

    def __init__(self, namespace: str, cluster_context: str, **kwargs):
        super().__init__(**kwargs)
        self.namespace = namespace
        self.cluster_context = cluster_context

    def get_client(self):
        try:
            from kubernetes import client, config

            config.load_kube_config(context=self.cluster_context)
            return client.CoreV1Api()
        except ImportError:
            raise StepExcecutionError("kubernetes client is required: pip install kubernetes")
        except Exception as err:
            raise StepExcecutionError(f"kubernetes client error: {err}")

    def process(self, inputs: Message) -> Message:
        raise NotImplementedError(
            "KubernetesStep is an abstract step and it should never be called directly."
        )


class ListNamespacedSecretStep(KubernetesStep):
    """
    List all the kubernetes secrets on the given namespace and context.
    Returns a Sequence/List with all the Secrets name in the namespace.
    """

    def process(self, inputs: Message) -> Message:
        try:
            client = self.get_client()
            response = client.list_namespaced_secret(namespace=self.namespace)
            secrets = [s.metadata.name for s in response.items if s.metadata]
            return SequenceMessage(secrets)
        except Exception as err:
            raise StepExcecutionError(
                f"error listing the secrets on namespace {self.namespace}: {err}"
            )


class ReadNamespacedSecretStep(KubernetesStep):
    """
    Downloads the kubernetes secret on the given namespace and context.
    """

    templated: t.Sequence[str] = tuple({"name"} | set(KubernetesStep.templated))

    def __init__(self, name: str, namespace: str, cluster_context: str, **kwargs):
        super().__init__(namespace, cluster_context, **kwargs)
        self.name = name

    def process(self, inputs: Message) -> Message:
        try:
            client = self.get_client()
            s = client.read_namespaced_secret(self.name, namespace=self.namespace)
            return MappingMessage(s.to_dict())
        except Exception as err:
            raise StepExcecutionError(
                f"error reading the secret {self.name} on namespace {self.namespace}: {err}"
            )


class CreateNamespacedSecretStep(KubernetesStep):
    """
    Creates a kubernetes secret on the given namespace and context.
    The input should be a MappingMessage with the secret data content.
    """

    templated: t.Sequence[str] = tuple({"name"} | set(KubernetesStep.templated))

    def __init__(self, name: str, namespace: str, cluster_context: str, **kwargs):
        """
        :param name of the secret
        :param namespace to use in Kubernetes
        :param cluster_context name to use
        """
        super().__init__(namespace, cluster_context, **kwargs)
        self.name = name

    def process(self, inputs: Message) -> Message:
        try:
            from kubernetes import client as v1

            client = self.get_client()
            s = client.create_namespaced_secret(
                namespace=self.namespace,
                body=v1.V1Secret(
                    api_version="v1",
                    data=inputs.get_value(),
                    kind="Secret",
                    metadata=v1.V1ObjectMeta(
                        name=self.name,
                        labels={},
                    ),
                    type="Opaque",
                ),
                pretty="true",
            )
            return MappingMessage(s.to_dict())
        except Exception as err:
            raise StepExcecutionError(
                f"error creating the secret {self.name} on namespace {self.namespace}: {err}"
            )


class ListNamespacedPodStep(KubernetesStep):
    """
    Returns a dictionary containing the pods with the "get pods" information:
    NAME                             READY   STATUS      RESTARTS   AGE
    {pod_name}                       1/1     Running     0          24h

    Using the following format:
    [{
        "name": {pod_name},
        "ready": [{ready}, {count}]
        "status": {status},
        "restarts": {restart_count},
        "age": {age_in_minutes}
    }]
    """

    def process(self, inputs: Message) -> Message:
        try:
            client = self.get_client()
            pods = client.list_namespaced_pod(namespace=self.namespace)
            items = []
            for p in pods.items:
                restarts = 0
                ready = 0
                containers = 0
                if (
                    p is not None
                    and p.status is not None
                    and p.status.container_statuses is not None
                ):
                    for cs in p.status.container_statuses:
                        restarts += cs.restart_count
                        ready = ready + 1 if cs.ready else ready
                    containers = len(p.status.container_statuses)
                st = pendulum.now() - pendulum.instance(p.status.start_time)
                items.append(
                    {
                        "name": p.metadata.name,
                        "ready": [ready, containers],
                        "status": p.status.phase,
                        "restarts": restarts,
                        "age": st.minutes,
                    }
                )
            return SequenceMessage(items)
        except Exception as err:
            raise StepExcecutionError(
                f"error listing the pods in the {self.namespace} namespace: {err}"
            )


class ReadNamespacedPodLog(KubernetesStep):
    """
    ReadNamespacedPodLog reads the log of the specified Pod and returns a list containing each line of the log as a list item.
    By default the pod_name is the input value. It could be:
    - string containing the pod name
    - tuple(str, str) containing the pod name and the container to tail.
    """

    templated: t.Sequence[str] = tuple({"pod_name", "container"} | set(KubernetesStep.templated))

    def __init__(
        self,
        namespace: str,
        cluster_context: str,
        pod_name: str = None,
        container: str = None,
        **kwargs,
    ):
        super().__init__(namespace, cluster_context, **kwargs)
        self.pod_name = pod_name
        self.container = container
        self.init = True if pod_name else False

    def process(self, inputs: Message) -> Message:
        if isinstance(inputs, ValueMessage) and not self.init:
            x = inputs.get_value()
            if isinstance(x, str):
                self.pod_name = x
                self.container = None
            elif isinstance(x, tuple):
                self.pod_name = x[0]
                self.container = x[1]
        try:
            client = self.get_client()
            r = client.read_namespaced_pod_log(
                namespace=self.namespace,
                name=self.pod_name,
                container=self.container,
                _preload_content=False,
            )
        except Exception as err:
            raise StepExcecutionError(
                f"error getting the log on pod {self.pod_name}/{self.container}: {err}"
            )
        logs = [str(line) for line in r.readlines()]
        return SequenceMessage(logs)
