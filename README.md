# vtjson

A lightweight package for validating JSON like Python objects.

## Schemas

Validation of JSON like Python objects is done according to a `schema` which is somewhat inspired by a typescript type. The format of a schema is more or less self explanatory as the following example shows.

### Example

Below is a simplified version of the schema of the run object in the mongodb database underlying the Fishtest web application <https://tests.stockfishchess.org/tests>

```python
import math
from datetime import datetime
from bson.objectid import ObjectId
from vtjson import glob, ip_address, number, regex, url

net_name = regex("nn-[a-z0-9]{12}.nnue", name="net_name")
tc = regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc")
str_int = regex(r"[1-9]\d*", name="str_int")
sha = regex(r"[a-f0-9]{40}", name="sha")
country_code = regex(r"[A-Z][A-Z]", name="country_code")
run_id = regex(r"[a-f0-9]{24}", name="run_id")
uuid = regex(r"[0-9a-zA-Z]{2,}(-[a-f0-9]{4}){3}-[a-f0-9]{12}", name="uuid")
epd_file = glob("*.epd", name="epd_file")
pgn_file = glob("*.pgn", name="pgn_file")

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
    "unique_key": uuid,
    "modified": bool,
    "ARCH": str,
    "nps": number,
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
    "tc_base": number,
    "base_same_as_master": bool,
    "rescheduled_from?": run_id,
    "approved": bool,
    "approver": str,
    "finished": bool,
    "deleted": bool,
    "failed": bool,
    "is_green": bool,
    "is_yellow": bool,
    "workers": int,
    "cores": int,
    "results": results_schema,
    "results_info?": {
        "style": str,
        "info": [str, ...],
    },
    "args": {
        "base_tag": str,
        "new_tag": str,
        "base_nets": [net_name, ...],
        "new_nets": [net_name, ...],
        "num_games": int,
        "tc": tc,
        "new_tc": tc,
        "book": union(epd_file, pgn_file),
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
            "state": union("", "accepted", "rejected"),
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
validate(schema, object, name="object", strict=True, subs={})
```

- The optional `name` argument is used to refer to the object being validated in the returned message.
- The optional argument `strict` indicates whether or not the object being validated is allowed to have keys/entries which are not in the schema.
- The optional argument `subs` is a dictionary whose keys are labels (see below) and whose values are substitution schemas for schemas with those labels.

## Wrappers

A wrapper takes one or more schemas as arguments and produces a new schema.

- An object matches the schema `union(schema1, ..., schemaN)` if it matches one of the schemas `schema1, ..., schemaN`.
- An object matches the schema `intersect(schema1, ..., schemaN)` if it matches all the schemas `schema1, ..., schemaN`.
- An object matches the schema `complement(schema)` if it does not match `schema`.
- An object matches the schema `lax(schema)` if it matches `schema` when validated with `strict=False`.
- An object matches the schema `strict(schema)` if it matches `schema` when validated with `strict=True`.
- An object matches the schema `set_name(schema, name)` if it matches `schema`. But the `name` argument will be used in non-validation messages.
- An object matches the schema `quote(schema)` if it is equal to `schema`. For example the schema `str` matches strings but the schema `quote(str)` matches the object `str`.
- An object matches the schema `set_label(schema, label1, ..., labelN, debug=False)` if it matches `schema`, unless the schema is replaced by a different one via the `subs` argument to `validate`. If the optional argument `debug` is `True` then a message will be printed on the console if the schema was changed.

## Built-ins

Some built-ins take arguments. If no arguments are given then the parentheses can be omitted. So `email` is equivalent to `email()`. Some built-ins have an optional `name` argument. This is used in non-validation messages.

- `regex(pattern, name=None, fullmatch=True, flags=0)`. This matches the strings which match the given pattern. By default the entire string is matched, but this can be overruled via the `fullmatch` argument. The `flags` argument has the usual meaning.
- `glob(pattern, name=None)`. Unix style filename matching. This is implemented using `pathlib.PurePath().match()`.
- `div(divisor, remainder=0, name=None)`. This matches the integers `x` such that `(x - remainder) % divisor` == 0.
- `number`. Matches `int` and `float`.
- `email`. Checks if the object is a valid email address. This uses the package `email_validator`. The `email` schema accepts the same options as `validate_email` in loc. cit.
- `ip_address` and `url`. These are similar to `email`.
- `domain_name(ascii_only=True, resolve=False)`. Checks if the object is a valid domain name. If `ascii_only=False` then allow IDNA domain names. If `resolve=True` check if the domain name resolves.
- `date_time(format=None)`. Without argument this represents an ISO 8601 date-time. The `format` argument represents a format string for `strftime`.
- `date` and `time`. These represent an ISO 8601 date and an ISO 8601 time.
- `anything`. Matches anything. This is functionally the same as just `object`.
- `nothing`. Matches nothing.

## Mixins

Mixins are built-ins that are usually combined with other schemas using `intersect`.

- `one_of(key1, ..., keyN)`. This represents a dictionary with exactly one key among `key1, ..., keyN`.
- `at_least_one_of(key1, ..., keyN)`. This represents a dictionary with a least one key among `key1, ..., keyN`.
- `at_most_one_of(key1, ..., keyN)`. This represents an dictionary with at most one key among `key1, ..., keyN`.
- `keys(key1, ..., keyN)`. This represents a dictionary containing all the keys in `key1, ..., keyN`.
- `interval(lb, ub, strict_lb=False, strict_ub=False)`. This checks if `lb <= object <= ub`, provided the comparisons make sense. An upper/lowerbound `...` (ellipsis) means that the corresponding inequality is not checked. The optional arguments `strict_lb`, `strict_ub` indicate whether the corresponding inequalities should be strict.
- `gt(lb)`. This checks if `object > lb`.
- `ge(lb)`. This checks if `object >= lb`.
- `lt(ub)`. This checks if `object < ub`.
- `le(ub)`. This checks if `object <= ub`.
- `size(lb, ub=None)`. Matches the objects (which support `len()` such as strings or lists) whose length is in the interval `[lb, ub]`. The value of `ub` can be `...` (ellipsis). If `ub=None` then `ub` is set to `lb`.
- `fields({field1: schema1, field2: schema2, ..., fieldN: schemaN})`. Matches Python objects with attributes `field1, field2, ..., fieldN` whose corresponding values should validate against `schema1, schema2, ..., schemaN` respectively.
- `magic(mime_type, name=None)`. Checks if a buffer (for example a string or a byte array) has the given mime type. This is implemented using the `python-magic` package.
- `filter(callable, schema, filter_name=None)`. Applies `callable` to the object and validates the result with `schema`. The optional argument `filter_name` is used in non-validation messages.

## Conditional schemas

- `ifthen(if_schema, then_schema, else_schema=None)`. If the object matches the `if_schema` then it should also match the `then_schema`. If the object does not match the `if_schema` then it should match the `else_schema`, if present.
- `cond((if_schema1, then_schema1), ... , (if_schemaN, then_schemaN))`. An object is successively validated against `if_schema1`, `if_schema2`, ... until a validation succeeds. When this happens the object should match the corresponding `then_schema`. If no `if_schema` succeeds then the object is considered to have been validated. If one sets `if_schemaN` equal to `anything` then this serves as a catch all.

## Pre-compiling a schema

An object matches the schema `compile(schema)` if it matches `schema`. `vtjson` compiles a schema before performing a validation against it, so pre-compiling is not necessary but it gains a bit of performance as it needs to be done only once. Compiling is an idempotent operation. It does nothing for an already compiled schema.

The full signature of `compile()` is

```python
compile(schema, _deferred_compiles=None)
```

but the optional argument `_deferred_compiles` should not be set by the user.

## Format

A schema can be, in order of precedence:

- A class with the following properties:

   - it has a no-argument constructor;
   - the instances have a `__validate__` method with signature

   ```python
   __validate__(self, object, name, strict, subs)
   ```

   - The parameters of `__validate__()` have the same semantics as those of `validate()`. The return value of `__validate__()` should be the empty string if validation succeeds, and otherwise it should be an explanation about what went wrong.

- An object having a `__validate__` attribute with signature

  ```python
  __validate__(object, name, strict, subs)
  ```

  as above.
- An object having a `__compile__` attribute with signature

  ```python
  __compile__(_deferred_compiles=None)
  ```

  This is an advanced feature which is used for the implementation of wrapper schemas. `__compile__()`, which is invoked by `compile()`, should produce an object with a `__validate__` attribute as described above. The optional argument `_deferred_compiles` is an opaque data structure for handling recursive schemas. It should be passed unmodified to any internal invocations of `compile()`. Please consult the source code of `vtjson` for more details.

- A Python type. In that case validation is done by checking membership.
- A callable. Validation is done by applying the callable to the object. If applying the callable throws an exception then the corresponding message will be part of the non-validation message.
- A `list` or a `tuple`. Validation is done by first checking membership of the corresponding types, and then performing validation for each of the entries of the object being validated against the corresponding entries of the schema.
- A dictionary. Validation is done by first checking membership of the `dict` type, and then performing validation for each of the values of the object being validated against the corresponding values of the schema. Keys are themselves considered as schemas. E.g. `{str: str}` represents a dictionary whose keys and values are both strings. A more elaborate discussion of validation of dictionaries is given below.
- A `set`. A set validates an object if the object is a set and the elements of the object are validated by an element of the schema.
- An arbitrary Python object. Validation is done by checking equality of the schema and the object, except when the schema is of type `float`, in which case `math.isclose` is used. Below we call such an object a `const schema`.

## Validating dictionaries

For a dictionary schema containing only `const keys` (i.e. keys corresponding to a `const schema`) the interpretation is obvious (see the introductory example above). Below we discuss the validation of an object against a dictionary schema in the general case.

- First we verify that the object is also a dictionary. If not then validation fails.
- We verify that all non-optional const keys of the schema are also keys of the object. If this is not the case then validation fails.
- Now we make a list of all the keys of the schema (both optional and non-optional). The result will be called the `key list` below.
- The object will pass validation if all its keys pass validation. We next discuss how to validate a particular key.
- If none of the entries of the key list validate the given key and `strict=True` (the default) then the key fails validation.
- We now match the given key against all entries of the key list. If it matches an entry and the corresponding value also validates then the key is validated. Otherwise we keep going through the key list.
- If the entire key list is consumed then the key fails validation.

A consequence of this algorithm is that non-const keys are automatically optional. So applying the wrapper `optional_key` to them is meaningless and has no effect.

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
make_type(schema, name=None, strict=True, debug=False, subs={})
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

A good source of more advanced examples is the file [`schemas.py`](https://raw.githubusercontent.com/official-stockfish/fishtest/master/server/fishtest/schemas.py) in the source distribution of Fishtest. Another source of examples is the file [`test_validate.py`](https://raw.githubusercontent.com/vdbergh/vtjson/main/test_validate.py) in the source distribution of `vtjson`.

## FAQ

Q: Why not just use the Python implementation of `JSON schema` (see <https://pypi.org/project/jsonschema/>)?

A: Various reasons.

- A `vtjson` schema is much more concise than a `JSON` schema!
- `vtjson` can validate objects which are more general than strictly `JSON`. See the introductory example above.
- More fundamentally, the design philosophy of `vtsjon` is different. A `JSON` schema  is language independent and fully declarative. These are very nice properties but, this being said, declarative languages have a tendency to suffer from feature creep as they try to deal with more and more exotic use cases (e.g. `css`).  A `vtjson` schema on the other hand leverages the versatility of the Python language. It is generally declarative, with a limited, but easily extendable set of primitives. But if more functionality is needed then it can be extended by using appropriate bits of Python code (as the `ordered_pair` example below illustrates). In practice this is what you will need in any case since a purely declarative language will never be able to deal with every possible validation scenario.

Q: Why yet another Python validation framework?

A: Good question! Initially `vtjson` consisted of home grown code for validating api calls and database accesses in the Fishtest framework. However the clear and concise schema format seemed to be of independent interest and so the code was refactored into the current self-contained package.

Q: Why are there no variables in `vtjson` (see <https://opis.io/json-schema/2.x/variables.html>)?

A: They did not seem to be essential yet. In our use cases conditional schemas were sufficient to achieve the required functionality. See for example the `action_schema` in [`schemas.py`](https://raw.githubusercontent.com/official-stockfish/fishtest/master/server/fishtest/schemas.py). More importantly `vtjson` has a strict separation between the definition of a schema and its subsequent use for validation. By allowing a schema to refer directly to the object being validated this separation would become blurred. This being said, I am still thinking about a good way to introduce variables.

Q: Does `vtjson` support recursive schemas?

A: Yes. But it requires a bit of Python gymnastics to create them. Here is an example

```python
person={}
person["mother"]=union(person, None)
person["father"]=union(person, None)
```

which matches e.g.

```python
{"father": {"father": None, "mother": None}, "mother": {"father": None, "mother": None}}
```

Note that you can create an infinite recursion by validating a recursive object against a recursive schema.

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

```python
schema = intersect((int, int), lambda o: o[0] <= o[1])
```
