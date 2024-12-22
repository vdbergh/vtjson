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
   :show-inheritance:

.. autoclass:: vtjson.glob
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.div
   :class-doc-from: both
   :show-inheritance:
		    
.. autoclass:: vtjson.close_to
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.email
   :class-doc-from: both
   :show-inheritance:
		    
.. autoclass:: vtjson.ip_address
   :class-doc-from: both
   :show-inheritance:
		    
.. autoclass:: vtjson.url
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.domain_name
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.date_time
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.date
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.time
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.anything
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.nothing
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.float_
   :class-doc-from: both
   :show-inheritance:

.. _modifiers:

Modifiers
---------

.. autoclass:: vtjson.one_of
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.at_least_one_of
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.at_most_one_of
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.keys
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.interval
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.gt
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.ge
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.lt
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.le
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.size
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.fields
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.magic
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.filter
   :class-doc-from: both
   :show-inheritance:


		    

.. _wrappers:

Wrappers
--------

Wrappers are schemas that contain references to other schemas.

.. autoclass:: vtjson.union
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.intersect
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.complement
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.lax
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.strict
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.quote
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.set_name
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.protocol
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.set_label
   :class-doc-from: both
   :show-inheritance:


Conditional schemas
-------------------

.. autoclass:: vtjson.ifthen
   :class-doc-from: both
   :show-inheritance:

.. autoclass:: vtjson.cond
   :class-doc-from: both
   :show-inheritance:


.. _type_annotations:

Type annotations integration
----------------------------

Type annotations as schemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^

`vtjson` recognizes the following type annotations as schemas.


		
:ref:`annotated`, :ref:`mapping`, :ref:`container`, :ref:`tuple`, :ref:`protocol`, :ref:`namedtuple`, :ref:`newtype`, :ref:`typeddict`, :ref:`union`, :ref:`any`.

For example `dict[str, str]` is translated internally into the schema `{str: str}`. This is explained further below.

.. _annotated:

Annotated
^^^^^^^^^

* More general vtjson schemas can work along Python type annotations by using the `typing.Annotated` contruct. The most naive way to do this is via

  .. code-block:: python

    Annotated[type_annotation, vtjson_schema, skip_first]


  For example

  .. code-block:: python

    Annotated[list[object], [int, str, float], skip_first]

    
  A type checker such as `mypy` will only see the type annotation (`list[object]` in the example), whereas vtjson will only see the vtjson schema (`[int, str, float]` in the example). `skip_first` is a built-in short hand for `Apply(skip_first=True)` (see below) which directs vtjson to ignore the first argument of an `Annotated` schema.
 
* In some use cases a `vtjon` schema will meaningfully refine a Python type or type annotation. In that case one should not use `skip_first`. For example:

   .. code-block:: python
		   
    Annotated[datetime, fields({"tzinfo": timezone.utc})]

  defines a `datetime` object whose time zone is `utc`.

* The built-in schemas already check that an object has the correct type. So for those one should use `skip_first`. For example:

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

.. _typeddict:

TypedDict
  A TypedDict type annotation is, roughly speaking, translated into a `dict` schema. E.g.

  .. code-block:: python

    class Movie(TypedDict):
      title: str
      price: float

  internally becomes

  .. code-block:: python

    set_name({"title": str, "price": float}, "Movie", reason=True)

  `vtjson` supports the `total` option to `TypedDict` as well as the `Required` and `NotRequired` annotations of fields, if they are compatible with the Python version being used.

.. _protocol:

Protocol
  A class implementing a protocol is translated into a :py:class:`vtjson.fields` schema. E.g.

  .. code-block:: python

    class Movie(Protocol):
      title: str
      price: float

  internally becomes

  .. code-block:: python

    set_name(fields({"title": str, "price": float}), "Movie", reason=True)

.. _namedtuple:

NamedTuple
  A `NamedTuple` class is translated into an :py:class:`vtjson.intersect` schema encompassing a `tuple` schema and a :py:class:`vtjson.fields` schema. E.g.

  .. code-block:: python
  
    class Movie(NamedTuple):
      title: str
      price: float

  internally becomes

  .. code-block:: python

    set_name(intersect(tuple, fields({"title": str, "price": float})), "Movie", reason=True)

Annotated
  This has already been discussed in the section :ref:`annotated`. It is translated into a suitable :py:class:`vtjson.intersect` schema. The handling of `Annotated` schemas can be influenced by :py:class:`vtjson.Apply` objects.

.. _newtype:

NewType
  This is translated into a :py:class:`vtjson.set_name` schema. E.g. `NewType('Movie', str)` becomes `set_name(str, 'Movie')`

.. _tuple:

tuple[...] and Tuple[...]
  These are translated into the equivalent `tuple` schemas.

.. _mapping:

Mapping[K, V] and subtypes
  These validate those objects that are members of the origin type (a subclass of `Mapping`) and whose (key, value) pairs match `(K, V)`.

.. _container:

Container[T] and subtypes
  These validate those objects that are members of the origin type (a subclass of `Container`) and whose elements match `T`.

.. _union:

Union and the | operator
  These are translated into :py:class:`vtjson.union`.

.. _literal:

Literal
  This is also translated into :py:class:`vtjson.union`.

.. _any:

Any
  This is translated into :py:class:`vtjson.anything`.

Apply objects
^^^^^^^^^^^^^

* If the list of arguments of an Annotated schema includes :py:class:`vtjson.Apply` objects then those modify the treatement of the arguments that come before them. We already encountered :py:data:`vtjson.skip_first` which is a built-in alias for `Apply(skip_first=True)`.

* Multiple :py:class:`vtjson.Apply` objects are allowed. E.g. the following contrived schema

  .. code-block:: python
  
    Annotated[int, str, skip_first, float, skip_first]

  is equivalent to `float`.

.. autoclass:: vtjson.Apply
   :class-doc-from: both
   :show-inheritance:

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

* A Python type. In that case validation is done by checking membership. For compatibility with Python type annotations, the schema `float` matches both ints and floats. Use :py:class:`vtjson.float_` if you want only floats.

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
   :show-inheritance:

Pre-compiling a schema
^^^^^^^^^^^^^^^^^^^^^^

An object matches the schema `compile(schema)` if it matches `schema`. `vtjson` compiles a schema before using it for validation, so pre-compiling is not necessary. However for large schemas it may gain some of performance as it needs to be done only once. Compiling is an idempotent operation. It does nothing for an already compiled schema.
		    

