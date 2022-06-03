from time import sleep
import walnut
from walnut import __version__


def sleep_step(params: dict = {}) -> dict:
    sleep(1)
    return {}


def error_step(params: dict = {}) -> dict:
    raise ValueError("this is an error")


def demo():
    walnut.Recipe(
        title=f"Walnut Demo v{__version__}",
        steps=[
            walnut.LambdaStep("Step 1", sleep_step),
            walnut.LambdaStep("Step 2", sleep_step),
            walnut.Section(
                title="Step 3 - Run LambdaSteps with Sleeps",
                steps=[
                    walnut.LambdaStep("Sleep 1/5", sleep_step),
                    walnut.LambdaStep("Sleep 2/5", sleep_step),
                    walnut.LambdaStep("Sleep 3/5", sleep_step),
                    walnut.LambdaStep("Sleep 4/5", sleep_step),
                    walnut.LambdaStep("Sleep 5/5", sleep_step),
                ]
            ),
            walnut.LambdaStep("Step 4", sleep_step),
            walnut.LambdaStep("Step 5", sleep_step),
            walnut.WarningStep("Warning!", "deprecation warning"),
            walnut.DebugStep(),
            walnut.LambdaStep("Step 6", sleep_step),
            # walnut.LambdaStep("Step in error", error_step)
        ]
    ).bake()


if __name__ == "__main__":
    demo()
