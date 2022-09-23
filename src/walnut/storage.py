import typing as t
from functools import reduce
from operator import getitem


class Storage:
    """
    Storage is a central place to store and retrieve values that can be used across Steps.
    All values are available to steps and parameters via the templating system:
    - `store.*` for Recipe store access.
    - `store.params.*` for Recipe parameters.
    E.g:
    ```
    {{ store.params.secrets.project }} == params["secrets"]["project"]
    ```
    """

    storage: t.Dict[t.Text, t.Any] = {
        # Params store the Recipe execution parameters read on preparation
        "params": {},
    }

    def __getitem__(self, key: str):
        """
        Lookup/Retrieve a value given its key and return None if not found
        """
        return self.storage.get(key)

    def __setitem__(self, key: str, value: t.Any):
        """
        Insert a key/value pair into the storage.
        """
        if "." in key:
            self.update_nested_item(key.split("."), value)
        else:
            self.storage[key] = value

    def __contains__(self, key: str):
        """
        Test for membership.
        """
        return key in self.storage

    def __delitem__(self, key: str):
        """
        Remove an item from the storage.
        """
        del self.storage[key]

    def as_dict(self) -> t.Dict:
        """
        Return the storage content as dictionary
        """
        return self.storage

    def update_nested_item(self, path, value):
        """Update item in nested dictionary"""
        reduce(getitem, path[:-1], self.storage)[path[-1]] = value
