import click

import walnut as w
from walnut import __version__


@click.command()
@click.option(
    "--env",
    default="qa",
    help="environment to use",
    type=click.Choice(["qa", "prod"], case_sensitive=False),
)
def airflow_observer(env):
    w.Recipe(
        title=f"Simple Walnut Demo v{__version__}",
        steps=[
            w.LambdaStep(fn=lambda x, y: {"V2FsbnV0"}),
            w.Base64DecodeStep(),
            test_debug_output_and_traces(),
            initiate_environment(),
            demo_foreach(),
            test_tree_structure(),
        ],
    ).prepare(
        params=w.ReadFileStep(filename="demo/simple/settings.json", callbacks=[w.SelectStep(env)]),
    ).bake()


def initiate_environment():
    return w.Section(
        title="Initializing the environment",
        steps=[
            # Add all your SetUp here
        ],
    )


def demo_foreach():
    return w.Section(
        title="Small Demo on ForEach",
        steps=[
            w.LambdaStep(fn=lambda x, y: {"one": 1, "two": 2, "three": 3}),
            w.ForEachStep(
                steps=[
                    w.LambdaStep(fn=lambda x, y: ["a", "b", "c"]),
                    w.ForEachStep(steps=[w.DummyStep(message="for each {{ inputs }}")]),
                    w.ForEachStep(
                        seq={"x": "-x-", "y": "-y-", "z": "-z-"},
                        steps=[w.DummyStep(message="for each {{ inputs }}")],
                    ),
                ]
            ),
            w.ForEachStep(
                seq=["g", "p", "u"], steps=[w.DummyStep(message="for each {{ inputs }}")]
            ),
        ],
    )


def test_tree_structure():
    return w.Section(
        title="node 1",
        steps=[
            w.DummyStep(title="node 1.1", message=""),
            w.DummyStep(
                title="node 1.2",
                message="",
                callbacks=[
                    w.DummyStep(title="node 1.2.1", message=""),
                    w.DummyStep(
                        title="node 1.2.2",
                        message="",
                        callbacks=[
                            w.DummyStep(title="node 1.2.2.1", message=""),
                            w.DummyStep(title="node 1.2.2.2", message=""),
                            w.DummyStep(title="node 1.2.2.3", message=""),
                        ],
                    ),
                    w.DummyStep(title="node 1.2.3", message=""),
                ],
            ),
            w.DummyStep(title="node 1.3", message=""),
        ],
    )


def test_debug_output_and_traces():
    return w.Section(
        title="Debug Output from Steps Sample",
        steps=[
            w.DummyStep(title="Print some message and add a trace", message="Hello World!"),
            w.TraceStep("{{ inputs }} I'm a trace"),
        ],
    )


if __name__ == "__main__":
    airflow_observer()
