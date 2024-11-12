# vtjson

A lightweight package for validating JSON like Python objects.

## Schemas

Validation of JSON like Python objects is done according to a `schema` which is somewhat inspired by a typescript type. The format of a schema is more or less self explanatory. As an [example](https://raw.githubusercontent.com/vdbergh/vtjson/refs/heads/main/docs/example1.md) one may consult the schema of the run object in the mongodb database underlying the Fishtest web application <https://tests.stockfishchess.org/tests>.

The following conventions are used:

- As in typescript, a (string) key ending in `?` represents an optional key. The corresponding schema (the item the key points to) will only be used for validation when the key is present in the object that should be validated. A key can also be made optional by wrapping it as `optional_key(key)`.
- If in a list/tuple the last entry is `...` (ellipsis) it means that the next to last entry will be repeated zero or more times. In this way generic types can be created. For example the schema `[str, ...]` represents a list of strings.

As of version 2.1, a suitable adapted `vtjson` schema can be used as a Python type hint. Here is the above [example](https://raw.githubusercontent.com/vdbergh/vtjson/refs/heads/main/docs/example2.md) rewritten in a way that is compatible with type hints. E.g. if one wants to ensure that a run object obtained via an api has the correct type one can do

```python
from typing import assert_type

def f(run_from_api: object, ...) -> ...:
    run = safe_cast(runs_schema, run_from_api)
    assert_type(run, runs_schema)   # Confirm that run has indeed the correct type now
```

If the cast succeeds then it means that the `run_from_api` object has been validated against the `runs_schema` and its type has been changed accordingly.

## Usage

To validate an object against a schema one can simply do

```python
validate(schema, object)
```

If the validation fails this will throw a `ValidationError` and the exception contains an explanation about what went wrong. The full signature of `validate` is

```python
validate(schema, object, name="object", strict=True, subs={})
```

- The optional argument `name` is used to refer to the object being validated in the returned message.
- The optional argument `strict` indicates whether or not the object being validated is allowed to have keys/entries which are not in the schema.
- The optional argument `subs` is a dictionary whose keys are labels (see below) and whose values are substitution schemas for schemas with those labels.

## Wrappers

A wrapper takes one or more schemas as arguments and produces a new schema.

- An object matches the schema `union(schema1, ..., schemaN)` if it matches one of the schemas `schema1, ..., schemaN`.
- An object matches the schema `intersect(schema1, ..., schemaN)` if it matches all the schemas `schema1, ..., schemaN`.
- An object matches the schema `complement(schema)` if it does not match `schema`.
- An object matches the schema `lax(schema)` if it matches `schema` when validated with `strict=False`.
- An object matches the schema `strict(schema)` if it matches `schema` when validated with `strict=True`.
- An object matches the schema `set_name(schema, name, reason=False)` if it matches `schema`, but the `name` argument will be used in non-validation messages. Unless `reason` is `True` the original non-validation message will be suppressed.
- An object matches the schema `protocol(schema, dict=False)` if `schema` is a class and its fields are annotated with schemas which validate the corresponding fields in the object. If `dict` is `True` then the object is validated as a `dict`.
- An object matches the schema `set_label(schema, label1, ..., labelN, debug=False)` if it matches `schema`, unless the schema is replaced by a different one via the `subs` argument to `validate`. If the optional argument `debug` is `True` then a message will be printed on the console if the schema was changed.

## Built-ins

Some built-ins take arguments. If no arguments are given then the parentheses can be omitted. So `email` is equivalent to `email()`. Some built-ins have an optional `name` argument. This is used in non-validation messages.

- `regex(pattern, name=None, fullmatch=True, flags=0)`. This matches the strings which match the given pattern. By default the entire string is matched, but this can be overruled via the `fullmatch` argument. The `flags` argument has the usual meaning.
- `glob(pattern, name=None)`. Unix style filename matching. This is implemented using `pathlib.PurePath().match()`.
- `div(divisor, remainder=0, name=None)`. This matches the integers `x` such that `(x - remainder) % divisor` == 0.
- `close_to(x, abs_tol=None, rel_tol=None)`. This matches the floats that are close to `x` in the sense of `math.isclose`.
- `email`. Checks if the object is a valid email address. This uses the package `email_validator`. The `email` schema accepts the same options as `validate_email` in loc. cit.
- `ip_address(version=None)`. Matches ip addresses of the specified version which can be 4, 6 or None.
- `url`. Matches valid urls.
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
- `filter(callable, schema, filter_name=None)`. Applies `callable` to the object and validates the result with `schema`. If the callable throws an exception then validation fails. The optional argument `filter_name` is used in non-validation messages.

## Conditional schemas

- `ifthen(if_schema, then_schema, else_schema=None)`. If the object matches the `if_schema` then it should also match the `then_schema`. If the object does not match the `if_schema` then it should match the `else_schema`, if present.
- `cond((if_schema1, then_schema1), ... , (if_schemaN, then_schemaN))`. An object is successively validated against `if_schema1`, `if_schema2`, ... until a validation succeeds. When this happens the object should match the corresponding `then_schema`. If no `if_schema` succeeds then the object is considered to have been validated. If one sets `if_schemaN` equal to `anything` then this serves as a catch all.

## Pre-compiling a schema

An object matches the schema `compile(schema)` if it matches `schema`. `vtjson` compiles a schema before using it for validation, so pre-compiling is not necessary. However for large schemas it may gain some of performance as it needs to be done only once. Compiling is an idempotent operation. It does nothing for an already compiled schema.

The full signature of `compile()` is

```python
compile(schema)
```

## Schema format

A schema can be, in order of precedence:

- An instance of the class `compiled_schema`.

  The class `compiled_schema` defines a single method with signature

   ```python
   __validate__(self, object, name, strict, subs)
   ```

  The parameters of `__validate__()` have the same semantics as those of `validate()`. The return value of `__validate__()` should be the empty string if validation succeeds, and otherwise it should be an explanation about what went wrong.

- A subclass of `compiled_schema` with a no-argument constructor.

- An object having a `__validate__` attribute with signature

  ```python
  __validate__(object, name, strict, subs)
  ```

  as above.
- An object having a `__compile__` attribute with signature

  ```python
  __compile__(_deferred_compiles=None)
  ```

  This is an advanced feature which is used for the implementation of wrapper schemas. The function `compile`, which was discussed above, internally invokes

  ```python
  _compile(schema, _deferred_compiles=None)
  ```

  where the optional argument `_deferred_compiles`  is an opaque data structure used for handling recursive schemas. If appropriate, the function `_compile` internally invokes the method `schema.__compile__` and this should produce an instance of the class `compiled_schema`. The method `__compile__` may invoke the function `_compile` again. If this happens then the optional argument `_deferred_compiles` should be passed unmodified. Please consult the source code of `vtjson` for more details.
- A Python type hint such as `list[str]`. This is discussed further below.
- A Python type. In that case validation is done by checking membership. By convention the schema `float` matches both ints and floats. Similarly the schema `complex` matches ints and floats besides of course complex numbers.
- A callable. Validation is done by applying the callable to the object. If applying the callable throws an exception then the corresponding message will be part of the non-validation message.
- An instance of `Sequence` that is not an instance of `str` (e.g a `list` or a `tuple`). Validation is done by first checking membership of the schema type, and then performing validation for each of the entries of the object being validated against the corresponding entries of the schema.
- An instance of `Mapping`. Validation is done by first checking membership of the schema type, and then performing validation for each of the values of the object being validated against the corresponding values of the schema. Keys are themselves considered as schemas. E.g. `{str: str}` represents a dictionary whose keys and values are both strings. A more elaborate discussion of validation of dictionaries is given below.
- A `set`. A set validates an object if the object is a set and the elements of the object are validated by an element of the schema.
- An arbitrary Python object. Validation is done by checking equality of the schema and the object, except when the schema is `float`, in which case `math.isclose` is used. Below we call such an object a `const schema`.

## Validating dictionaries

For a dictionary schema containing only `const keys` (i.e. keys corresponding to a `const schema`) the interpretation is obvious (see the introductory example above). Below we discuss the validation of an object against a dictionary schema in the general case.

- First we verify that the object is also a dictionary. If not then validation fails.
- We verify that all non-optional const keys of the schema are also keys of the object. If this is not the case then validation fails.
- Now we make a list of all the keys of the schema (both optional and non-optional). The result will be called the `key list` below.
- The object will pass validation if all its keys pass validation. We next discuss how to validate a particular key of the object.
- If none of the entries of the key list validate the given key and `strict==True` (the default) then the key fails validation. If on the other hand `strict==False` then the key passes.
- Assuming the fate of the given key hasn't been decided yet, we now match it against all entries of the key list. If it matches an entry and the corresponding value also validates then the key is validated. Otherwise we keep going through the key list.
- If the entire key list is consumed then the key fails validation.

A consequence of this algorithm is that non-const keys are automatically optional. So applying the wrapper `optional_key` to them is meaningless and has no effect.

## Type hints integration

### Type hints as schemas

`vtjson` recognizes the following type hints as schemas.

```python
Annotated, dict[...], Dict[...], list[...], List[...], tuple[...], Tuple[...],
Protocol, NamedTuple, Literal, NewType, TypedDict, Union (or the equivalent operator |).
```

For example `dict[str, str]` is translated internally into the schema `{str: str}`. See below for more information.

### Annotated

- More general vtjson schemas can work along Python type hints by using the `typing.Annotated` contruct. The most naive way to do this is via

  ```python
  Annotated[type_hint, vtjson_schema, skip_first]
  ```

  For example

  ```python
  Annotated[list[object], [int, str, float], skip_first]
  ```

  A type checker such as `mypy` will only see the type hint (`list[object]` in the example), whereas vtjson will only see the vtjson schema (`[int, str, float]` in the example). `skip_first` is a built-in short hand for `Apply(skip_first=True)` (see below) which directs vtjson to ignore the first argument of an `Annotated` schema.
- In some use cases a vtjon_schema will meaningfully refine a Python type or type hint. In that case one should not use `skip_first`. For example:

  ```python
  Annotated[datetime, fields({"tzinfo": timezone.utc})]
  ```

  defines a `datetime` object whose time zone is `utc`.

  The built-in schemas already check that an object has the correct type. So for those one should use `skip_first`. For example:

  ```python
  Annotated[int, div(2), skip_first]
  ```

  matches even integers.
- If one wants to pre-compile a schema and still use it as a type hint (assuming it is valid as such) then one can do:

  ```python
  schema = <schema definition>
  Schema = Annotated[schema, compile(schema), skip_first]
  ```

### Supported type hints

Note that Python imposes strong restrictions on what constitutes a valid type hint but `vtjson` is much more lax about this. Enforcing the restrictions is left to the type checkers or the Python interpreter.

- `TypedDict`. A TypedDict type hint is translated into a `dict` schema. E.g.

  ```python
  class Movie(TypedDict):
      title: str
      price: float
  ```

  internally becomes `{"title": str, "price": float}`. `vtjson` supports the `total` option to `TypedDict` as well as the `Required` and `NotRequired` annotations of fields, if they are compatible with the Python version being used.

- `Protocol`. A class implementing a protocol is translated into a `fields` schema. E.g.

  ```python
  class Movie(Protocol):
      title: str
      price: float
  ```

  internally becomes `fields({"title": str, "price": float})`.

- `NamedTuple`. A `NamedTuple` class is translated as the intersection of a `tuple` schema and a fields schema. E.g.

  ```python
  class Movie(NamedTuple):
      title: str
      price: float
  ```

  internally becomes `intersect(tuple, fields({"title": str, "price": float}))`.

- `Annotated` has already been discussed. It is translated into a suitable `intersect` schema. The handling of `Annotated` schemas can be influenced by `Apply` objects (see below).

- `NewType` is translated into a `set_name` schema. E.g. `NewType('Movie', str)` becomes `set_name(str, 'Movie')`

- `dict[...]` and `Dict[...]` are translated into the equivalent `dict` schemas. E.g. `dict[str, str]`  becomes `{str: str}`.

- `tuple[...]` and `Tuple[...]` are translated into the equivalent `tuple` schemas.

- `list[...]` and `List[...]` are translated into the equivalent `list` schemas.

- `Union` and the `|` operator are translated into `union`.

- `Literal` is also translated into `union`.

### Apply objects

- If the list of arguments of an Annotated schema includes Apply objects then those modify the treatement of the arguments that come before them. We already encountered `skip_first` which is a built-in alias for `Apply(skip_first=True)`. The full signature of `Apply` is

  ```python
  Apply(skip_first=False, name=None, labels=None)
  ```

  The optional `name` argument indicates that the corresponding `set_name` command should be applied to the previous arguments. The optional `labels` argument (a list if present) indicates that the corresponding `set_label` command should be applied to the previous arguments.

- Multiple `Apply` objects are allowed. E.g. the following contrived schema

  ```python
  Annotated[int, str, skip_first, float, skip_first]
  ```

  is equivalent to `float`.

### Safe cast

Vtjson includes the command

```python
safe_cast(schema, object)
```

(where `schema` should be a valid type hint) that functions exactly like `cast` except that it also verifies at run time that the given object matches the given schema.

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
>>> from vtjson import set_name, union, validate
>>> schema = {"fruit" : union("apple", "pear", "strawberry"), "price" : float}
>>> object = {"fruit" : "dog", "price": 1.0 }
>>> validate(schema, object)
...
vtjson.ValidationError: object['fruit'] (value:'dog') is not equal to 'pear' and object['fruit'] (value:'dog') is not equal to 'strawberry' and object['fruit'] (value:'dog') is not equal to 'apple'
>>> fruit = set_name(union("apple", "pear", "strawberry"), "fruit")
>>> schema = {"fruit" : fruit, "price" : float}
>>> validate(schema, object)
...
vtjson.ValidationError: object['fruit'] (value:'dog') is not of type 'fruit'
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

A: Use `intersect` (or `Annotated` if applicable). For example the following schema validates positive integers but reject positive floats.

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
