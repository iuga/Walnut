from typing import Sequence
from walnut import Step
from walnut.errors import StepExcecutionError


class KubernetesStep(Step):
    """
    Base and Abstract Step to interact with Kubernetes. All Steps that require 
    Kubernetes access should inherit from this class.
    """

    templated: Sequence[str] = tuple({"namespace", "context"} | set(Step.templated))

    def __init__(self, title: str, namespace: str, context: str):
        super().__init__(title)
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

    def execute(self, params: dict) -> dict:
        return NotImplemented("KubernetesStep should not be called directly")


class GetSecretStep(KubernetesStep):
    """
    Downloads the kubernetes secret on the given namespace and context and stores the
    result in {kubernetes}.{secrets}.{SECRET_NAME} as a dictionary.
    """

    templated: Sequence[str] = tuple({"name"} | set(Step.templated))

    def __init__(self, title: str, name: str, namespace: str, context: str):
        super().__init__(title, namespace, context)
        self.name = name

    def execute(self, params: dict) -> dict:
        try:
            client = self.get_client()
            s = client.read_namespaced_secret(self.name, namespace=self.namespace)
            return {
                "kubernetes": {
                    "secrets": {
                        self.name: s.to_dict()
                    }
                }
            }
        except Exception as err:
            raise StepExcecutionError(f"kubernetes client error: {err}")
