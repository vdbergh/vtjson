# validate
A package for validating JSON like Python objects.

## Schemas

Validation of JSON like Python objects is done according to a "schema" which is somewhat inspired by a typescript type. The format of a schema is more or less self explanatory as the following example shows.

### Example

Below is the schema of the run object in the mongodb database underlying the Fishtest web application https://tests.stockfishchess.org/tests

```python
from datetime import datetime
from bson.objectid import ObjectId
from numbers import Real  # matches int and float
from validate import ip_address, regex, union, url

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
            "elo_model": "normalized",
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
## Conventions
- As in typescript, a (string) key ending in "?" represents an optional key. The corresponding schema (the item the key points to) will only be used for validation when the key is present in the object that should be validated. A key can also be made optional by wrapping it as `optional_key(key)`.
- If in a list/tuple the last entry is `...` (`ellipsis`) it means that the next to last entry will be repeated zero or more times. In this way generic types can be created. For example the schema `[str, ...]` represents a list of strings.
- The schema may contain tuples, even though these are not valid JSON. In fact any Python object is a valid schema (see below).
## Usage
- To validate an object against a schema one can simply do
  ```python
  explanation = validate(schema, object)
  ```  
  If the validation is succesful then the return value is the empty string. Otherwise it contains an explanation what went wrong.
  The full signature of `validate` is
  ```python
  validate(schema, object, name="object", strict=True)
  ```
  - The optional `name` argument is used to refer to the object being validated in the returned message.
  - The optional argument `strict` indicates whether or not the object being validated is allowed to have keys/entries which are not in the schema.
- A cool feature of the package is that one can can transform a schema into a genuine Python type via
  ```python
  t = make_type(schema)
  ```
  so that validation can be done via
  ```python
  isinstance(object, t)
  ```
  The drawback, compared to using `validate` directly, is that there is no feedback when validation fails. You can get it back as a console debug message via the optional `debug` argument to `make_type`.
  The full signature of `make_type` is
  ```python
  make_type(schema, name=None, strict=True, debug=False)
  ```
  The optional `name` argument is used to set the `__name__` attribute of the type. If it is not supplied then the package tries to make an educated guess.
## Wrappers
A wrapper takes one or more schemas as arguments and produces a new schema.
- An object matches the schema `union(schema1, schema2)` if it matches `schema1` or `schema2`. Unions of more than two schemas are also valid.
- An object matches the schema `intersect(schema1, schema2)` if it matches `schema1` and `schema2`. Intersections of more than two schemas are also valid.
- An object matches the schema `lax(schema)` when it matches `schema` with `strict=False`, see below.
- An object matches the schema `strict(schema)` when it matches `schema` with `strict=True`, see below.
## Built-ins
- `regex(pattern, name=None, fullmatch=True)`. This matches the strings which match the given pattern. The optional `name` argument may be used to give the regular expression a descriptive name. By default the entire string is matched, but this can be overruled via the `fullmatch` argument.
- `email`, `ip_address` and `url`. These match strings with the implied format.
## Format
A schema can be, in order of precedence:
- An object having a `__validate__` attribute with signature
  ```python
  __validate__(object, name, strict)
  ```
  This is for example how the `union` and `regex` schemas are implemented internally. The parameters and the return value of `__validate__()` have the same semantics as those of `validate()`, as discussed above.
- A Python type. In that case validation is done by checking membership.
- A `list` or a `tuple`. Validation is done by first checking membership of the corresponding types, and then performing validation for each of the entries of the object being validated against the corresponding entries of the schema.
- A dictionary. Validation is done by first checking membership of the `dict` type, and then performing validation for each of the items of the object being validated against the corresponding items of the schema.
- An arbitrary Python object. Validation is done by checking equality of the schema and the object.
## Examples
```python
>>> from validate import make_type, union, validate
>>> schema = {"fruit" : union("apple", "pear", "strawberry"), "price" : float}
>>> object = {"fruit" : "dog", "price": 1.0 }
>>> validate(schema, object)
"object['fruit'] (value:dog) is not equal to 'apple' and object['fruit'] (value:dog) is not equal to 'pear' and object['fruit'] (value:dog) is not equal to 'strawberry'"
>>> fruit = make_type(union("apple", "pear", "strawberry"), name="fruit")
>>> schema = {"fruit" : fruit, "price" : float}
>>> validate(schema, object)
"object['fruit'] (value:dog) is not of type fruit"
>>> object = {"fruit" : "apple"}
>>> validate(schema, object)
"object['price'] is missing"
```
