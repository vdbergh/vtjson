# vtjson

`vtjson` is an easy to use validation library compatible with Python type annotations.

## Introduction

Here is a simple schema:

```python
book_schema = {
    "title": str,
    "authors": [str, ...],
    "editor?": str,
    "year": int,
}
```

The following conventions were used:

- As in typescript, a (string) key ending in `?` represents an optional key. The corresponding schema (the item the key points to) will only be used for validation when the key is present in the object that should be validated. A key can also be made optional by wrapping it with `optional_key`.
- If in a list/tuple the last entry is `...` (ellipsis) it means that the next to last entry will be repeated zero or more times. In this way generic types can be created. For example the schema `[str, ...]` represents a list of strings.

Let's try to validate some book objects:

```python
good_book = {
    "title": "Gone with the Wind",
    "authors": ["Margaret Mitchell"],
    "year": 1936,
}

bad_book = {
    "title": "Gone with the Wind",
    "authors": ["Margaret Mitchell"],
    "year": "1936",
}

validate(book_schema, good_book, name="good_book")
validate(book_schema, bad_book, name="bad_book")
```

As expected `vtjson` throws an exception for the second object:

```text
Traceback (most recent call last):
          ...
    raise ValidationError(message)
vtjson.vtjson.ValidationError: bad_book['year'] (value:'1936') is not of type 'int'
```

We may also rewrite the `book_schema` as a valid Python type annotation.

```python
class book_schema(TypedDict):
    title: str
    authors: list[str]
    editor: NotRequired[str]
    year: int
```

Attempting to validate the bad book would raise the same exception as before.

Schemas can of course be more complicated and in particular they can be nested.
Here is an example that shows more of the features of `vtjson`.

```python
person_schema = {
    "name": regex("[a-zA-Z. ]*"),
    "email?": email,
    "website?": url,
}

book_schema = {
    "title": str,
    "authors": [person_schema, ...],
    "editor?": person_schema,
    "year": intersect(int, ge(1900)),
}
```

Let's try to validate an object not fitting the schema.

```python
bad_book = {
    "title": "Gone with the Wind",
    "authors": [{"name": "Margaret Mitchell", "email": "margaret@gmailcom"}],
    "year": "1936",
}
```

```text
Traceback (most recent call last):
          ...
    raise ValidationError(message)
vtjson.vtjson.ValidationError: bad_book['authors'][0]['email'] (value:'margaret@gmailcom') is not of type 'email': The part after the @-sign is not valid. It should have a period.
```

As before we can rewrite the new `book_schema` as a valid type annotation.

```python
class person_schema(TypedDict):
    name: Annotated[str, regex("[a-zA-Z. ]*")]
    email: NotRequired[Annotated[str, email]]
    website: NotRequired[Annotated[str, url]]

class book_schema(TypedDict):
    title: str
    authors: list[person_schema]
    editor: NotRequired[list[person_schema]]
    year: Annotated[int, ge(1900)]
```

For comprehensive documentation about `vtjson` see [https://www.cantate.be/vtjson](https://www.cantate.be/vtjson) (canonical reference) or [https://vtjson.readthedocs.io](https://vtjson.readthedocs.io).
