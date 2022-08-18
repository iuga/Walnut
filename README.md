# Walnut
Walnut is a small Python data processing engine designed for reliable production data pipelines and tooling.

```python
import walnut as w

response = w.Recipe(
    title=f"Powered by Walnut",
    steps=[
        # Read the logs from a Kubernetes Pod running in the cluster
        ReadNamespacedPodLog(
            namespace="{{ store.params.namespace }}", context="mainCluster",
            pod_name="scheduler", container="scheduler"
        ),
        # Subset all the lines in the log containing Exception
        w.TextSubsetStep(".*Exception.*"),
        # Require an empty list
        w.RequireEmptyStep(),
    ],
).prepare({
    # Some execution parameters:
    "namespace": "myNamespace"
}).bake()
```

### Installation

```
pip install git+https://github.com/iuga/walnut
```

### Api Reference

- `core`
  - `Recipe`
  - `Section`
  - `ForEachStep`
- `steps`
  - `DummyStep`
  - `StoreOutputStep`
  - `LambdaStep`
  - `ReadFileStep`
  - `Base64DecodeStep`
  - `mutate`
    - `SelectStep`
    - `FilterStep`
    - `MapStep`
    - `ReduceStep`
  - `assert`
    - `AssertEqualStep`
    - `AssertAllInStep`
    - `AssertEmptyStep`
    - `AssertNotEmptyStep`
    - `AssertChecksStep`
    - `AssertGreaterStep`
    - `AssertLessStep`
    - `AssertGreaterOrEqualStep`
    - `AssertLessOrEqualStep`
  - `require`
      - `RequireEqualStep`
      - `RequireAllInStep`
      - `RequireEmptyStep`
      - `RequireNotEmptyStep`
      - `RequireChecksStep`
      - `RequireGreaterStep`
      - `RequireLessStep`
      - `RequireGreaterOrEqualStep`
      - `RequireLessOrEqualStep`
  - `text`
      - `TextSubsetStep`
      - `TextToLowerStep`
      - `TextToUpperStep`
      - `TextJoinStep`
      - `TextSplitStep`
      - `TextCountStep`
      - `TextReplaceStep`

### What's next?
...


### Examples
...
