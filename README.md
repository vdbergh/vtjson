# vtjson
A lightweight package for validating JSON like Python objects.

## Schemas

Validation of JSON like Python objects is done according to a `schema` which is somewhat inspired by a typescript type. The format of a schema is more or less self explanatory as the following example shows.

### Example

Below is the schema of the run object in the mongodb database underlying the Fishtest web application https://tests.stockfishchess.org/tests

```python
import math
from datetime import datetime
from bson.objectid import ObjectId
from vtjson import ip_address, number, regex, url

net_name = regex("nn-[a-z0-9]{12}.nnue", name="net_name")
tc = regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc")
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
    "compiler": {"clang++", "g++"},
    "unique_key": str,
    "modified": bool,
    "ARCH": str,
    "nps": number,
    "near_github_api_limit": bool,
    "remote_addr": ip_address,
    "country_code": {country_code, "?"},
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
    "tc_base": number,
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
        "throughput": number,
        "itp": number,
        "priority": number,
        "adjudication": bool,
        "sprt?": {
            "alpha": 0.05,
            "beta": 0.05,
            "elo0": number,
            "elo1": number,
            "elo_model": "normalized",
            "state": {"", "accepted", "rejected"},
            "llr": number,
            "batch_size": int,
            "lower_bound": -math.log(19),
            "upper_bound": math.log(19),
            "lost_samples?": int,
            "illegal_update?": int,
            "overshoot?": {
                "last_update": int,
                "skipped_updates": int,
                "ref0": number,
                "m0": number,
                "sq0": number,
                "ref1": number,
                "m1": number,
                "sq1": number,
            },
        },
        "spsa?": {
            "A": number,
            "alpha": number,
            "gamma": number,
            "raw_params": str,
            "iter": int,
            "num_iter": int,
            "params": [
                {
                    "name": str,
                    "start": number,
                    "min": number,
                    "max": number,
                    "c_end": number,
                    "r_end": number,
                    "c": number,
                    "a_end": number,
                    "a": number,
                    "theta": number,
                },
                ...,
            ],
            "param_history?": [
                [{"theta": number, "R": number, "c": number}, ...],
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
            "residual?": number,
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
            "residual": number,
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
- As in typescript, a (string) key ending in `?` represents an optional key. The corresponding schema (the item the key points to) will only be used for validation when the key is present in the object that should be validated. A key can also be made optional by wrapping it as `optional_key(key)`.
- If in a list/tuple the last entry is `...` (ellipsis) it means that the next to last entry will be repeated zero or more times. In this way generic types can be created. For example the schema `[str, ...]` represents a list of strings.
## Usage
To validate an object against a schema one can simply do
```python
validate(schema, object)
```  
If the validation fails this will throw a `ValidationError` and the exception contains an explanation about what went wrong. The full signature of `validate` is
```python
validate(schema, object, name="object", strict=True)
```
- The optional `name` argument is used to refer to the object being validated in the returned message.
- The optional argument `strict` indicates whether or not the object being validated is allowed to have keys/entries which are not in the schema.
## Wrappers
A wrapper takes one or more schemas as arguments and produces a new schema. **Warning:** wrappers should be considered as being immutable. In other words: if the underlying schemas change after a wrapper has been created then the effect of validating against the wrapper is undefined. If you _really_ need this then you should recreate the wrapper.
- An object matches the schema `union(schema1, ..., schemaN)` if it matches one of the schemas `schema1, ..., schemaN`. This is almost the same as `{schema1, ..., schemaN}`, or equivalently `set((schema1, ..., schemaN))` if `schema1, ..., schemaN` are hashable.
- An object matches the schema `intersect(schema1, ..., schemaN)` if it matches all the schemas `schema1, ..., schemaN`.
- An object matches the schema `complement(schema)` if it does not match `schema`.
- An object matches the schema `lax(schema)` if it matches `schema` when validated with `strict=False`.
- An object matches the schema `strict(schema)` if it matches `schema` when validated with `strict=True`.
- An object matches the schema `set_name(schema, name)` if it matches `schema`. But the `name` argument will be used in non-validation messages.
- An object matches the schema `compile(schema)` if it matches `schema`. `vtjson` compiles the schema before performing a validation so pre-compiling is not necessary but, in some cases, it may gain a bit of performance. 
- An object matches the schema `quote(schema)` if it is equal to `schema`. For example the schema `{"cats", "dogs"}` matches the strings `"cats"` and `"dogs"` but the schema `quote({"cats", "dogs"})` matches the set `{"cats", "dogs"}`. 
## Built-ins
Some built-ins take arguments. If no arguments are given then the parentheses can be omitted. So `email` is equivalent to `email()`.
- `regex(pattern, name=None, fullmatch=True, flags=0)`. This matches the strings which match the given pattern. The optional `name` argument may be used to give the regular expression a descriptive name. By default the entire string is matched, but this can be overruled via the `fullmatch` argument. The `flags` argument has the usual meaning.
- `interval(lowerbound, upperbound)`. This checks if `lowerbound <= object <= upperbound`, provided the comparisons make sense. An upper/lowerbound `...` (ellipsis) means that the
corresponding inequality is not checked.
- `number`. Matches `int` and `float`.
- `email`. Checks if the object is a valid email address. This uses the package `email_validator`. The `email` schema accepts the same options as `validate_email` in loc. cit.
- `ip_address` and `url`. These are similar to `email`.
- `domain_name(ascii_only=True, resolve=False)`. Checks if the object is a valid domain name. If `ascii_only=False` then allow IDNA domain names. If `resolve=True` check if the domain name resolves.
- `date_time(format=None)`. Without argument this represents an ISO 8601 date-time. The `format` argument represents a format string for `strftime`.
- `date` and `time`. These represent an ISO 8601 date and an ISO 8601 time.
- `one_of(*args)`. This represents a dictionary with exactly one key in `args` (the intention is that this will be combined with the schema of a dictionary, containing optional keys, using `intersect`).
- `at_least_one_of(*args)`. This represents a dictionary with a least one key in `args`.
- `at_most_one_of(*args)`. This represents a dictionary with at most one key in `args`.
## Format
A schema can be, in order of precedence:
- A class with the following properties:
  - it has a no-argument constructor;
  - the instances have a `__validate__` method with signature
  ```python
  __validate__(self, object, name, strict)
  ```
  - The parameters of `__validate__()` have the same semantics as those of `validate()`. The return value of `__validate__()` should be the empty string if validation succeeds, and otherwise it should be an explanation about what went wrong.
- An object having a `__validate__` attribute with signature
  ```python
  __validate__(object, name, strict)
  ```
  as above. This is for example how the wrapper schemas are implemented internally.
- A Python type. In that case validation is done by checking membership.
- A callable. Validation is done by applying the callable to the object. If applying the callable throws an exception then the corresponding message will be part of the non-validation message.
- A `list` or a `tuple`. Validation is done by first checking membership of the corresponding types, and then performing validation for each of the entries of the object being validated against the corresponding entries of the schema.
- A dictionary. Validation is done by first checking membership of the `dict` type, and then performing validation for each of the items of the object being validated against the corresponding items of the schema.
- A `set`. A set validates an object, if one of its members does.
- An arbitrary Python object. Validation is done by checking equality of the schema and the object, except when the schema is of type `float`, in which case `math.isclose` is used.
## Creating types
A cool feature of `vtjson` is that one can transform a schema into a genuine Python type via
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
The optional `name` argument is used to set the `__name__` attribute of the type. If it is not supplied then `vtjson` tries to make an educated guess.
## Examples
```python
>>> from vtjson import set_name, validate
>>> schema = {"fruit" : {"apple", "pear", "strawberry"}, "price" : float}
>>> object = {"fruit" : "dog", "price": 1.0 }
>>> validate(schema, object)
...
vtjson.ValidationError: object['fruit'] (value:dog) is not equal to 'pear' and object['fruit'] (value:dog) is not equal to 'strawberry' and object['fruit'] (value:dog) is not equal to 'apple'
>>> fruit = set_name({"apple", "pear", "strawberry"}, "fruit")
>>> schema = {"fruit" : fruit, "price" : float}
>>> validate(schema, object)
...
vtjson.ValidationError: object['fruit'] (value:dog) is not of type 'fruit'
>>> object = {"fruit" : "apple"}
>>> validate(schema, object)
...
vtjson.ValidationError: object['price'] is missing
```
For many more examples see the file `test_validate.py` in the source distribution.
## FAQ
Q: Why not just use the Python implementation of `JSON schema` (see https://pypi.org/project/jsonschema/)?

A: Various reasons.
- A `vtjson` schema is much more concise than a `JSON` schema!
- `vtjson` can validate objects which are more general than strictly `JSON`. See the introductory example above. 
- More fundamentally, the design philosophy of `vtsjon` is different. A `JSON` schema  is language independent and fully declarative. These are very nice properties but, this being said, declarative languages have a tendency to suffer from feature creep as they try to deal with more and more exotic use cases (e.g. `css`).  A `vtjson` schema on the other hand leverages the versatility of the Python language. It is generally declarative, with a limited, but easily extendable set of primitives. But if more functionality is needed then it can be extended by using appropriate bits of Python code (as the `ordered_pair` example below illustrates). In practice this is what you will need in any case since a purely declarative language will never be able to deal with every possible validation scenario. 

Q: How is this different from https://pypi.org/project/json-checker/ \?

A: Good question! I discovered `json-checker` after I had written `vtjson`. Although the details are different `json-checker` and `vtjson` share many of the same principles.

Q: How to combine validations?

A: Use `intersect`. For example the following schema validates positive integers but reject positive floats.
```python
schema = intersect(int, interval(0, ...))
```
More generally one may use the pattern `intersect(schema, more_validations)` where the first argument makes sure that the object to be validated has the required layout to be an acceptable input for the later arguments. For example an ordered pair of integers can be validated using the schema
```python
def ordered_pair(o):
    return o[0] <= o[1]
schema = intersect((int, int), ordered_pair)
```
Or in a one liner
```python
schema = intersect((int, int), set_name(lambda o: o[0] <= o[1], "ordered_pair"))
```
The following also works if you are content with less nice output on validation failure (try it)
```
schema = intersect((int, int), lambda o: o[0] <= o[1])
```
