"""
Google Cloud Platform - Security & Identity

This module provide steps to:
- Manage secrets on Google Cloud.
- etc
"""
import typing as t
from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import Message, ValueMessage


class SecretManagerStep(Step):
    """
    Secret Manager is a secure and convenient storage system for API keys, passwords,
    certificates, and other sensitive data. Secret Manager provides a central place and
    single source of truth to manage, access, and audit secrets across Google Cloud.
    """

    templated: t.Sequence[str] = tuple({"project_id"} | set(Step.templated))

    def __init__(self, project_id: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.project_id = project_id
        try:
            from google.cloud import secretmanager_v1

            self.client = secretmanager_v1.SecretManagerServiceClient()
        except ImportError as err:
            raise StepExcecutionError(f"Missing dependency. Plese execute pip install google-cloud-secret-manager: {err}")

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        raise NotImplementedError("Please do not use SecretManagerStep. Use a child class instead.")


class SecretsVersionsAccessStep(SecretManagerStep):
    """
    Manage secret versions: Access a secret version's data
    > gcloud secrets versions access 1 --secret MY_PASSWORD --project my-project
    """

    templated: t.Sequence[str] = tuple({"secret"} | set(SecretManagerStep.templated))

    def __init__(self, secret: str = None, version: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.secret = secret
        self.version = version

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        from google.cloud import secretmanager_v1
        request = secretmanager_v1.AccessSecretVersionRequest(
            name="projects/{}/secrets/{}/versions/{}".format(
                self.project_id,
                self.secret,
                self.version
            ),
        )
        response = self.client.access_secret_version(request=request)
        return ValueMessage(response.payload.data.decode("utf-8"))
