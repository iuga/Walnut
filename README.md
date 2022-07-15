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
).bake({
    # Some execution parameters:
    "namespace": "myNamespace"
})
```

### Installation

```
pip install git+https://github.com/iuga/walnut
```

### What's next?
...


### Examples
...
