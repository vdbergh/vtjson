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

.. autofunction:: vtjson.validate
.. autoexception:: vtjson.ValidationError
.. autoexception:: vtjson.SchemaError

Schema format
-------------

A schema can be, in order of precedence:

* An instance of the class :py:class:`vtjson.compiled_schema`.

  .. autoclass:: vtjson.compiled_schema

  The class :py:class:`vtjson.compiled_schema` defines a single method with similar semantics as  :py:func:`vtjson.validate`.
  
  .. automethod:: vtjson.compiled_schema.__validate__

