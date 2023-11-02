# validate
A package to validate json like data

## Schemas

Validation is done according to a "schema". The format of a schema is more or less self explanatory as the following example shows.

### Example

Below is the schema of the run object in the mongodb database underlying the Fishtest web application https://tests.stockfishchess.org/tests

```python
from bson.objectid import ObjectId
from numbers import Real  # matches int and float
from fishtest.validate import ip_address, regex, union, url

net_name = regex("nn-[a-z0-9]{12}.nnue", name="net_name")
tc = regex(r"^([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?$", name="tc")
str_int = regex(r"[1-9]\d*", name="str_int")
sha = regex(r"[a-f0-9]{40}", name="sha")
country_code = regex(r"[A-Z][A-Z]", name="country_code")
run_id = regex(r"[a-f0-9]{24}", name="run_id")

worker_info_schema = {
    "uname": str,
    "architecture": [str, str],
    "concurrency": int,
    "max_memory": int,
    "min_threads": int,
    "username": str,
    "version": int,
    "python_version": [int, int, int],
    "gcc_version": [int, int, int],
    "compiler": union("clang++", "g++"),
    "unique_key": str,
    "modified": bool,
    "ARCH": str,
    "nps": Real,
    "near_github_api_limit": bool,
    "remote_addr": ip_address,
    "country_code": union(country_code, "?"),
}

results_schema = {
    "wins": int,
    "losses": int,
    "draws": int,
    "crashes": int,
    "time_losses": int,
    "pentanomial": [int, int, int, int, int],
}

schema = {
    "_id?": ObjectId,
    "start_time": datetime,
    "last_updated": datetime,
    "tc_base": Real,
    "base_same_as_master": bool,
    "results_stale?": bool,
    "rescheduled_from?": run_id,
    "approved": bool,
    "approver": str,
    "finished": bool,
    "deleted": bool,
    "failed": bool,
    "is_green": bool,
    "is_yellow": bool,
    "workers?": int,
    "cores?": int,
    "results": results_schema,
    "results_info?": {
        "style": str,
        "info": [str, ...],
    },
    "args": {
        "base_tag": str,
        "new_tag": str,
        "base_net": net_name,
        "new_net": net_name,
        "num_games": int,
        "tc": tc,
        "new_tc": tc,
        "book": str,
        "book_depth": str_int,
        "threads": int,
        "resolved_base": sha,
        "resolved_new": sha,
        "msg_base": str,
        "msg_new": str,
        "base_options": str,
        "new_options": str,
        "info": str,
        "base_signature": str_int,
        "new_signature": str_int,
        "username": str,
        "tests_repo": url,
        "auto_purge": bool,
        "throughput": Real,
        "itp": Real,
        "priority": Real,
        "adjudication": bool,
        "sprt?": {
            "alpha": Real,
            "beta": Real,
            "elo0": Real,
            "elo1": Real,
            "elo_model": union("BayesElo", "logistic", "normalized"),
            "state": union("", "accepted", "rejected"),
            "llr": Real,
            "batch_size": int,
            "lower_bound": Real,
            "upper_bound": Real,
            "lost_samples?": int,
            "illegal_update?": int,
            "overshoot?": {
                "last_update": int,
                "skipped_updates": int,
                "ref0": Real,
                "m0": Real,
                "sq0": Real,
                "ref1": Real,
                "m1": Real,
                "sq1": Real,
            },
        },
        "spsa?": {
            "A": Real,
            "alpha": Real,
            "gamma": Real,
            "raw_params": str,
            "iter": int,
            "num_iter": int,
            "params": [
                {
                    "name": str,
                    "start": Real,
                    "min": Real,
                    "max": Real,
                    "c_end": Real,
                    "r_end": Real,
                    "c": Real,
                    "a_end": Real,
                    "a": Real,
                    "theta": Real,
                },
                ...,
            ],
            "param_history?": [
                [{"theta": Real, "R": Real, "c": Real}, ...],
                ...,
            ],
        },
    },
    "tasks": [
        {
            "num_games": int,
            "active": bool,
            "last_updated": datetime,
            "start": int,
            "residual?": Real,
            "residual_color?": str,
            "bad?": True,
            "stats": results_schema,
            "worker_info": worker_info_schema,
        },
        ...,
    ],
    "bad_tasks?": [
        {
            "num_games": int,
            "active": False,
            "last_updated": datetime,
            "start": int,
            "residual": Real,
            "residual_color": str,
            "bad": True,
            "task_id": int,
            "stats": results_schema,
            "worker_info": worker_info_schema,
        },
        ...,
    ],
}
```
## Comments

- A key ending in "?" represents an optional key. The corresponding schema (the item the key points to) will only be used for validation when the key is present in the object that should be validated.
- If in a list/tuple the last entry is `...` (`ellipsis`) it means that the next to last entry will be repeated zero or more times. Example: `[str, ...]`.
- An object matches `union(schema1, schema2)` if it matches `schema1` or `schema2`.
- Strings can be validated using regular expressions.
- The package contains some predefined schemas. Currently these are `email`, `ip_address` and `url`.
- The schema accepts tuples, even though these are not valid json. In fact the schema is an arbitrary Python object (see below).

## Usage
- To validate an object against a schema one can simply do
  ```python
  message = validate(schema, object)
  ```  
  If the validation is succesful then the return value `message` is the empty string. Otherwise it contains an explanation what when wrong.
  The full signature of `validate` is
  ```python
  validate(schema, object, name="instance", strict=False)
  ```
  The optional argument `strict` indicates whether or not the object being validated is allowed to have keys/entries which are not in the schema.
- A cool feature of the package is that you can transform a schema into a genuine Python type via
  ```python
  t = make_type(schema)
  ```
  so that validation can be done via
  ```python
  isinstance(object, t)
  ```
  The drawback, compared to using `validate` directly, is that you get no feedback when validation fails. You can get it back as a console debug message via the optional `debug` argument to `make_type`.
  The full signature of `make_type` is
  ```python
  make_type(schema, name=None, strict=False, debug=False)
  ```
- A schema can be, in order of precedence:
- - An object having a `__validate__` attribute with signature
    ```python
    __validate__(self, object, name, strict=False)
    ```
    This is how internally the `union` and `regex` schemas are implemented.
  - A Python type. In that case validation is simply done by checking membership.
  - A `list` or a `tuple`. Validation is done recursively.
  - A dictionary. Validation is done recursively for the items.
  - An arbitrary Python object. Validation is done by checking equality of the schema and the object.
