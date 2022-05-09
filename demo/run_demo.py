from time import sleep
import walnut
from walnut import steps, __version__


def sleep_step(params: dict = {}) -> dict:
    sleep(1)
    return {}


def error_step(params: dict = {}) -> dict:
    raise ValueError("this is an error")


def demo():
    walnut.Recipe(
        title=f"Walnut Demo v{__version__}",
        steps=[
            walnut.LambdaStep("Sleep 1/5", sleep_step),
            walnut.LambdaStep("Sleep 2/5", sleep_step),
            walnut.LambdaStep("Sleep 3/5", sleep_step),
            walnut.LambdaStep("Sleep 4/5", sleep_step),
            walnut.LambdaStep("Sleep 5/5", sleep_step),
            walnut.WarningStep("Warning!", "deprecation warning"),
            # walnut.LambdaStep("Step in error", error_step)
        ]
    ).bake()


if __name__ == "__main__":
    demo()

