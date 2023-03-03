import typing as t

from walnut.errors import StepExcecutionError, StepValidationError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage
from walnut.steps.core import Step


def validate_input_type(types: t.Optional[t.List[t.Type[Message]]] = None):
    """
    validate_input_type validates the Message input type.
    It's a helper decorator to create simpler and more robust steps. E.g:
    ```
    @validate_input_type(types=[ValueMessage])
    def process(self, inputs: Message) -> Message:
        ...
    ```
    """
    ALL_MESSAGE_TYPES = [ValueMessage, SequenceMessage, MappingMessage]
    types = ALL_MESSAGE_TYPES if types is None or len(types) == 0 else types

    def wrap(fn):
        def inner(stepClass, inputs: t.Optional[Message] = None, *args, **kwargs):
            if not stepClass or not isinstance(stepClass, Step):
                raise StepValidationError(
                    f"decorator validate_input_type can only be used on a Step class: {stepClass}"
                )
            if not inputs:
                raise StepValidationError(
                    "decorator validate_input_type can only be used on the Step inputs"
                )
            if not isinstance(inputs, tuple(types)):
                raise StepExcecutionError(
                    f"{stepClass} requires input types {[t.__name__ for t in types]} but had {inputs}"
                )
            return fn(stepClass, inputs, *args, **kwargs)

        return inner

    return wrap
