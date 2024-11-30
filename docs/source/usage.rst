Usage
=====

Installation
------------

`vtjson` is available via pip:

.. code-block:: console

   $ pip install vtjson

Tutorial
--------

.. testsetup:: *

   from vtjson import email, make_type, safe_cast, url, validate

Here is a simple schema:

.. testcode::

   book_schema = {
     "title": str,
     "authors": [str, ...],
     "editor?": str,
     "year": int,
   }

The following conventions were used:

* As in typescript, a (string) key ending in `?` represents an optional key. The corresponding schema (the item the key points to) will only be used for validation when the key is present in the object that should be validated. A key can also be made optional by wrapping it as :py:func:`vtjson.optional_key`.
* If in a list/tuple the last entry is `...` (ellipsis) it means that the next to last entry will be repeated zero or more times. In this way generic types can be created. For example the schema `[str, ...]` represents a list of strings.

Let's try to validate some book objects:

.. testcode::

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

As expected `vtjson` throws an exception for the second object:

.. testoutput::

  Traceback (most recent call last):
      ...
      raise ValidationError(message)
  vtjson.vtjson.ValidationError: bad_book['year'] (value:'1936') is not of type 'int'

We can turn the `book_schema` into a genuine Python type.

.. testcode::

   Book = make_type(book_schema)

   print(f"Is good_book an instance of Book? {isinstance(good_book, Book)}!")
   print(f"Is bad_book an instance of Book? {isinstance(bad_book, Book)}!")

.. testoutput::

   Is good_book an instance of Book? True!
   Is bad_book an instance of Book? False!


We may also rewrite the `book_schema` as a valid Python type annotation.

.. testcode::

   from typing import NotRequired, TypedDict

   class book_schema(TypedDict):
     title: str
     authors: list[str]
     editor: NotRequired[str]
     year: int

Attempting to validate the bad book raises the same exception as before:

.. testcode::

   validate(book_schema, bad_book, name="bad_book")

.. testoutput::

  Traceback (most recent call last):
      ...
      raise ValidationError(message)
  vtjson.vtjson.ValidationError: book['year'] (value:'1936') is not of type 'int'

:py:func:`vtjson.safe_cast` functions exactly like `cast` except that it also verifies at run time that the given object matches the given schema.
  
.. testcode::

   book2 = safe_cast(book_schema, good_book)
   book3 = safe_cast(book_schema, bad_book)

The exception thrown is similar.

.. testoutput::

   Traceback (most recent call last):
       ...
       raise ValidationError(message)
   vtjson.vtjson.ValidationError: object is not of type 'book_schema': object['year'] (value:'1936') is not of type 'int'

Schemas can of course be nested

.. testcode::
   
   person_schema = {
     "name": str,
     "email?": email,
     "website?": url,
   }

   book_schema = {
     "title": str,
     "authors": [person_schema, ...],
     "editor?": person_schema,
     "year": int,
   }

`email` and `url` are built-in schemas. See :ref:`builtins`.

Let's validate an object not fitting the schema.

.. testcode::

   bad_book = {
     "title": "Gone with the Wind",
     "authors": [{"name": "Margaret Mitchell", "email":"margaret@gmailcom"}, ...],
     "year": "1936",
   }

   validate(book_schema, bad_book, name="bad_book")

.. testoutput::

   Traceback (most recent call last):
       ...
       raise ValidationError(message)
   vtjson.vtjson.ValidationError: bad_book['authors'][0]['email'] (value:'margaret@gmailcom') is not of type 'email': The part after the @-sign is not valid. It should have a period.

As before we can rewrite the new `book_schema` as a valid type annotation

.. testcode::
   
   from typing import Annotated

   class person_schema(TypedDict):
     name: str
     email: NotRequired[Annotated[str, email]]
     website: NotRequired[Annotated[str, url]]

   class book_schema(TypedDict):
     title: str
     authors: list[person_schema]
     editor: NotRequired[list[person_schema]]
     year: int

The contraint that a string should be an email address cannot be expressed in the language of type annotations. That's where `typing.Annotated` comes in:

.. testcode::
   
   Annotated[str, email]

Type checkers such as `mypy` only see the `str` part of this schema, but `vtjson` sees everything. For more information see :ref:`type_annotations`.

Let's check that validation also works with type annotations:

.. testcode::

   validate(book_schema, bad_book, name="bad_book")

.. testoutput::

   Traceback (most recent call last):
       ...
       raise ValidationError(message)
   vtjson.vtjson.ValidationError: bad_book is not of type 'book_schema': bad_book['authors'][0] is not of type 'person_schema': bad_book['authors'][0]['email'] (value:'margaret@gmailcom') is not of type 'email': The part after the @-sign is not valid. It should have a period.


   
Validating objects
------------------
To validate an object against a schema one may use :py:func:`vtjson.validate`. If validation fails this throws a :py:exc:`vtjson.ValidationError`.
A suitable written schema can be used as a Python type annotation. :py:func:`vtjson.safe_cast` verifies if a given object has a given type.
:py:func:`vtjson.make_type` transforms a schema into a genuine Python type so that validation can be done using `isinstance()`.


.. autofunction:: vtjson.validate
.. autofunction:: vtjson.safe_cast
.. autofunction:: vtjson.make_type

.. autoexception:: vtjson.ValidationError
.. autoexception:: vtjson.SchemaError

.. _builtins:

Built-in schemas
----------------

Some built-in schemas take arguments. If no arguments are given then the parentheses can be omitted. So `email` is equivalent to `email()`. Some built-ins have an optional `name` argument. This is used in non-validation messages.

.. autoclass:: vtjson.regex
   :class-doc-from: both

.. autoclass:: vtjson.glob
   :class-doc-from: both

.. autoclass:: vtjson.div
   :class-doc-from: both
		    
.. autoclass:: vtjson.close_to
   :class-doc-from: both

.. autoclass:: vtjson.email
   :class-doc-from: both
		    
.. autoclass:: vtjson.ip_address
   :class-doc-from: both
		    
.. autoclass:: vtjson.url
   :class-doc-from: both

.. autoclass:: vtjson.domain_name
   :class-doc-from: both

.. autoclass:: vtjson.date_time
   :class-doc-from: both

.. autoclass:: vtjson.date
   :class-doc-from: both

.. autoclass:: vtjson.time
   :class-doc-from: both

.. autoclass:: vtjson.anything
   :class-doc-from: both

.. autoclass:: vtjson.nothing
   :class-doc-from: both

Wrappers
--------

Wrappers may be used to combine a collection of schemas into a new schema.

.. autoclass:: vtjson.union
   :class-doc-from: both

.. autoclass:: vtjson.intersect
   :class-doc-from: both

.. autoclass:: vtjson.complement
   :class-doc-from: both

.. autoclass:: vtjson.lax
   :class-doc-from: both

.. autoclass:: vtjson.strict
   :class-doc-from: both

.. autoclass:: vtjson.set_name
   :class-doc-from: both

.. autoclass:: vtjson.protocol
   :class-doc-from: both

.. autoclass:: vtjson.set_label
   :class-doc-from: both

.. _type_annotations:

Type annotations integration
----------------------------

Schema format
-------------

A schema can be, in order of precedence:

* An instance of the class :py:class:`vtjson.compiled_schema`.   The class :py:class:`vtjson.compiled_schema` defines a single abstract method :py:meth:`vtjson.compiled_schema.__validate__` with similar semantics as  :py:func:`vtjson.validate`.

* A subclass of :py:class:`vtjson.compiled_schema` with a no-argument constructor.

* An object having a `__validate__()` attribute with the same signature as  :py:meth:`vtjson.compiled_schema.__validate__`.

* An instance of the class :py:class:`vtjson.wrapper`. The class :py:class:`vtjson.wrapper` defines a single abstract method :py:meth:`vtjson.wrapper.__compile__` that should produce an instance  of :py:class:`vtjson.compiled_schema`.

* A Python type annotation such as `list[str]`. See :ref:`type_annotations`.

* A Python type. In that case validation is done by checking membership. By convention the schema `float` matches both ints and floats. Similarly the schema `complex` matches ints and floats besides of course complex numbers.

* A callable. Validation is done by applying the callable to the object. If applying the callable throws an exception then the corresponding message will be part of the non-validation message.

* An instance of `Sequence` that is not an instance of `str` (e.g a `list` or a `tuple`). Validation is done by first checking membership of the schema type, and then performing validation for each of the entries of the object being validated against the corresponding entries of the schema.

* An instance of `Mapping`. Validation is done by first checking membership of the schema type, and then performing validation for each of the values of the object being validated against the corresponding values of the schema. Keys are themselves considered as schemas. E.g. `{str: str}` represents a dictionary whose keys and values are both strings. For a more elaborate discussion of validation of mappings see :ref:`mapping_schemas`.

* A `set`. A set validates an object if the object is a set and the elements of the object are validated by an element of the schema.

* An arbitrary Python object. Validation is done by checking equality of the schema and the object, except when the schema is `float`, in which case `math.isclose` is used. Below we call such an object a `const schema`.

.. autoclass:: vtjson.compiled_schema
  :members: __validate__

.. autofunction:: vtjson.compile

.. autofunction:: vtjson._compile

.. autoclass:: vtjson.wrapper
  :members: __compile__

.. _mapping_schemas:

Validating against Mapping schemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a Mapping schema containing only `const keys` (i.e. keys corresponding to a `const schema`) the interpretation is obvious. Below we discuss the validation of an object against a Mapping schema in the general case.

* First we verify that the type of the object is a subtype of the type of the schema. If not then validation fails.
* We verify that all non-optional const keys of the schema are also keys of the object. If this is not the case then validation fails.
* Now we make a list of all the keys of the schema (both optional and non-optional). The result will be called the `key list` below.
* The object will pass validation if all its keys pass validation. We next discuss how to validate a particular key of the object.
* If none of the entries of the key list validate the given key and `strict==True` (the default) then the key fails validation. If on the other hand `strict==False` then the key passes.
* Assuming the fate of the given key hasn't been decided yet, we now match it against all entries of the key list. If it matches an entry and the corresponding value also validates then the key is validated. Otherwise we keep going through the key list.
* If the entire key list is consumed then the key fails validation.

A consequence of this algorithm is that non-const keys are automatically optional. So applying the wrapper :py:func:`vtjson.optional_key` to them is meaningless and has no effect.

.. autoclass:: vtjson.optional_key
   :class-doc-from: both
