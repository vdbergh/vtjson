API reference
=============

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

.. _modifiers:

Modifiers
---------

.. autoclass:: vtjson.one_of
   :class-doc-from: both

.. autoclass:: vtjson.at_least_one_of
   :class-doc-from: both

.. autoclass:: vtjson.at_most_one_of
   :class-doc-from: both

.. autoclass:: vtjson.keys
   :class-doc-from: both

.. autoclass:: vtjson.interval
   :class-doc-from: both

.. autoclass:: vtjson.gt
   :class-doc-from: both

.. autoclass:: vtjson.ge
   :class-doc-from: both

.. autoclass:: vtjson.lt
   :class-doc-from: both

.. autoclass:: vtjson.le
   :class-doc-from: both

.. autoclass:: vtjson.size
   :class-doc-from: both

.. autoclass:: vtjson.fields
   :class-doc-from: both

.. autoclass:: vtjson.magic
   :class-doc-from: both

.. autoclass:: vtjson.filter
   :class-doc-from: both


		    

.. _wrappers:

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

Conditional schemas
-------------------

.. autoclass:: vtjson.ifthen
   :class-doc-from: both

.. autoclass:: vtjson.cond
   :class-doc-from: both


.. _type_annotations:

Type annotations integration
----------------------------

Type annotations as schemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^

`vtjson` recognizes the following type annotations as schemas.

.. code-block:: text
		
  Annotated, Mapping[...,...] and subtypes, Container[...] and subtypes,
  tuple[...], Tuple[...], Protocol, NamedTuple, Literal, NewType, TypedDict,
  Union (or the equivalent operator |), Any.

For example `dict[str, str]` is translated internally into the schema `{str: str}`. This is explained further below.

Annotated
^^^^^^^^^

* More general vtjson schemas can work along Python type annotations by using the `typing.Annotated` contruct. The most naive way to do this is via

  .. code-block:: python

    Annotated[type_annotation, vtjson_schema, skip_first]
    
  A type checker such as `mypy` will only see the type annotation (`list[object]` in the example), whereas vtjson will only see the vtjson schema (`[int, str, float]` in the example). `skip_first` is a built-in short hand for `Apply(skip_first=True)` (see below) which directs vtjson to ignore the first argument of an `Annotated` schema.
 
* In some use cases a `vtjon` schema will meaningfully refine a Python type or type annotation. In that case one should not use `skip_first`. For example:

  .. code-block:: python
		
    Annotated[int, div(2), skip_first]

  matches even integers.

* If one wants to pre-compile a schema and still use it as a type annotation (assuming it is valid as such) then one can do:

  .. code-block:: python

    schema = <schema definition>
    Schema = Annotated[schema, compile(schema), skip_first]

Supported type annotations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Note that Python imposes strong restrictions on what constitutes a valid type annotation but `vtjson` is much more lax about this. Enforcing the restrictions is left to the type checkers or the Python interpreter.

* `TypedDict`. A TypedDict type annotation is translated into a `dict` schema. E.g.

  .. code-block:: python

    class Movie(TypedDict):
      title: str
      price: float

  internally becomes `{"title": str, "price": float}`. `vtjson` supports the `total` option to `TypedDict` as well as the `Required` and `NotRequired` annotations of fields, if they are compatible with the Python version being used.

* `Protocol`. A class implementing a protocol is translated into a :py:class:`vtjson.fields` schema. E.g.

  .. code-block:: python

    class Movie(Protocol):
      title: str
      price: float

  internally becomes `fields({"title": str, "price": float})`.

* `NamedTuple`. A `NamedTuple` class is translated an :py:class:`vtjson.intersect` schema encompassing a `tuple` schema and a :py:class:`vtjson.fields` schema. E.g.

  .. code-block:: python
  
    class Movie(NamedTuple):
      title: str
      price: float

  internally becomes `intersect(tuple, fields({"title": str, "price": float}))`.

* `Annotated` has already been discussed. It is translated into a suitable :py:class:`vtjson.intersect` schema. The handling of `Annotated` schemas can be influenced by `Apply` objects.

* `NewType` is translated into a :py:class:`vtjson.set_name` schema. E.g. `NewType('Movie', str)` becomes `set_name(str, 'Movie')`

* `tuple[...]` and `Tuple[...]` are translated into the equivalent `tuple` schemas.

* `Mapping[S, T]` and subtypes validate those objects that are members of the origin type (a subclass of `Mapping`) and whose (key, value) pairs match `(S, T)`.

* `Container[T]` and subtypes validate those objects that are members of the origin type (a subclass of `Container`) and whose elements match `T`.

* `Union` and the `|` operator are translated into :py:class:`vtjson.union`.

* `Literal` is also translated into :py:class:`vtjson.union`.

* `Any` is translated into :py:class:`vtjson.anything`.

Apply objects
^^^^^^^^^^^^^

* If the list of arguments of an Annotated schema includes :py:class:`vtjson.Apply` objects then those modify the treatement of the arguments that come before them. We already encountered :py:data:`vtjson.skip_first` which is a built-in alias for `Apply(skip_first=True)`.

* Multiple :py:class:`vtjson.Apply` objects are allowed. E.g. the following contrived schema

  .. code-block:: python
  
    Annotated[int, str, skip_first, float, skip_first]

  is equivalent to `float`.

.. autoclass:: vtjson.Apply
   :class-doc-from: both

.. py:data:: vtjson.skip_first
  :type: vtjson.Apply
  :value: vtjson.Apply(skip_first=True)

   Do not use the first argument (the Python type annotation) in an `Annotated` construct for validation (likely because it is already covered by the other arguments).

  
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
