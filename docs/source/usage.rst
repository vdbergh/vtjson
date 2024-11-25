Usage
=====

Installation
------------

``vtjson`` is available via pip:

.. code-block:: console

   $ pip install vtjson

Validating objects
------------------
To validate an object against a schema one uses :py:func:`vtjson.validate`. If validation fails this throws a :py:exc:`vtjson.ValidationError`.
A suitable written schema can be used as a Python type annotation. :py:func:`vtjson.safe_cast` verifies if a given object has a given type.
:py:func:`vtjson.make_type` transforms a schema into a genuine Python type so that validation can be done using ``isinstance()``.


.. autofunction:: vtjson.validate
.. autofunction:: vtjson.safe_cast
.. autofunction:: vtjson.make_type

.. autoexception:: vtjson.ValidationError
.. autoexception:: vtjson.SchemaError

Schema format
-------------

A schema can be, in order of precedence:

* An instance of the class :py:class:`vtjson.compiled_schema`.   The class :py:class:`vtjson.compiled_schema` defines a single method :py:meth:`vtjson.compiled_schema.__validate__` with similar semantics as  :py:func:`vtjson.validate`.

* A subclass of :py:class:`vtjson.compiled_schema` with a no-argument constructor.

* An object having a ``__validate__()`` attribute with the same signature as  :py:meth:`vtjson.compiled_schema.__validate__`.

.. autoclass:: vtjson.compiled_schema
  
.. automethod:: vtjson.compiled_schema.__validate__

