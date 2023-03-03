import pytest

import walnut as w
from walnut.errors import StepExcecutionError
from walnut.messages import MappingMessage, Message, ValueMessage
from walnut.steps.core import Step
from walnut.steps.validators import validate_input_type


class ValidatedStep(Step):
    @validate_input_type(types=[ValueMessage])
    def process(self, inputs: Message) -> Message:
        return inputs


def test_simple_type_validator_success():
    assert (
        w.Recipe(
            title="Testing Recipe",
            steps=[w.LambdaStep(fn=lambda x, y: ValueMessage("walnut")), ValidatedStep()],
        )
        .prepare()
        .bake()
        == "walnut"
    )


def test_simple_type_validator_fail():
    with pytest.raises(StepExcecutionError):
        w.Recipe(
            title="Testing Recipe",
            steps=[w.LambdaStep(fn=lambda x, y: MappingMessage({})), ValidatedStep()],
        ).prepare().bake()
