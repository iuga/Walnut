import typing as t
from random import random
from time import sleep
import walnut
from walnut import __version__


def sleep_step(
    inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any], params: t.Dict[t.ByteString, t.Any]
) -> t.Dict[t.Any, t.Any]:
    sleep(1)
    return {}


def error_step(
    inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any], params: t.Dict[t.ByteString, t.Any]
) -> t.Dict[t.Any, t.Any]:
    raise ValueError("this is an error")


def we_only_have_access_to_a_copy_of_store(
    inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any], params: t.Dict[t.ByteString, t.Any]
) -> t.Dict[t.Any, t.Any]:
    store["the-key"] = "the-value"
    return {}


def generate_random_number(
    inputs: t.Dict[t.Any, t.Any], store: t.Dict[t.Any, t.Any], params: t.Dict[t.ByteString, t.Any]
) -> t.Dict[t.Any, t.Any]:
    return {
        "n": random() 
    }


def demo():
    walnut.Recipe(
        title=f"Walnut Demo v{__version__}",
        steps=[
            walnut.LambdaStep(sleep_step, title="Step 1"),
            walnut.LambdaStep(sleep_step, title="Step 2"),
            walnut.Section(
                title="Step 3 - Run LambdaSteps with Sleeps",
                steps=[
                    walnut.LambdaStep(sleep_step, title="Step 1/5"),
                    walnut.LambdaStep(sleep_step, title="Step 2/5"),
                    walnut.LambdaStep(sleep_step, title="Step 3/5"),
                    walnut.LambdaStep(sleep_step, title="Step 4/5"),
                    walnut.LambdaStep(sleep_step, title="Step 5/5"),
                ],
            ),
            walnut.LambdaStep(sleep_step, title="Step 4"),
            walnut.LambdaStep(sleep_step, title="Step 5"),
            walnut.DebugStep(),
            walnut.LambdaStep(sleep_step, title="Step 6"),
            walnut.LambdaStep(we_only_have_access_to_a_copy_of_store, title="Trying to modify the store"),
            walnut.DebugStep(),
            walnut.LambdaStep(generate_random_number, title="Generate a Random Number I"),
            walnut.DebugStep(),
            walnut.LambdaStep(generate_random_number, title="Generate a Random Number II"),
            walnut.StoreOutputStep("random_number_2"),
            walnut.DebugStep(),
            #walnut.LambdaStep(error_step, title="Step in Error"),
        ],
    ).bake({"env": "dev"})


if __name__ == "__main__":
    demo()
