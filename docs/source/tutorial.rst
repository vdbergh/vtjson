Getting started
===============

Installation
------------

`vtjson` is available via pip:

.. code-block:: console

   $ pip install vtjson


   
Tutorial
--------

.. testsetup:: *

   from vtjson import email, ge, intersect, make_type, regex, safe_cast, skip_first, url, validate

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

Attempting to validate the bad book raises a similar exception as before:

.. testcode::

   validate(book_schema, bad_book, name="bad_book")

.. testoutput::

  Traceback (most recent call last):
      ...
      raise ValidationError(message)
  vtjson.vtjson.ValidationError: bad_book is not of type 'book_schema': bad_book['year'] (value:'1936') is not of type 'int'

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

Schemas can of course be more complicated and in particular they can be nested

.. testcode::
   
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

:py:class:`regex`, :py:class:`email` and :py:class:`url` are built-in schemas. See :ref:`builtins`. :py:class:`intersect` is a `wrapper`. See :ref:`wrappers`. :py:class:`ge` is a `modifier`. See :ref:`modifiers`. It should be obvious that the schema

.. testcode::

   intersect(int, ge(1900))

represents an integer greater or equal than 1900.

Let's validate an object not fitting the schema.

.. testcode::

   bad_book = {
     "title": "Gone with the Wind",
     "authors": [{"name": "Margaret Mitchell", "email":"margaret@gmailcom"}],
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
   
   from typing import Annotated, NotRequired, TypedDict

   class person_schema(TypedDict):
     name: Annotated[str, regex("[a-zA-Z. ]*")]
     email: NotRequired[Annotated[str, email]]
     website: NotRequired[Annotated[str, url]]

   class book_schema(TypedDict):
     title: str
     authors: list[person_schema]
     editor: NotRequired[person_schema]
     year: Annotated[int, ge(1900)]

Many constraints expressible in `vtjson` schemas cannot be expressed in the language of type annotations. That's where `typing.Annotated` comes in. Consider the following example:

.. testcode::
   
   Annotated[str, email]

Type checkers such as `mypy` only see the `str` part of this schema, but `vtjson` sees everything. For more information see :ref:`type_annotations`. There is a small caveat here: :py:class:`email` in fact already checks that the object is a string. So as further explained in :ref:`type_annotations`, it is more efficient to write:

.. testcode::

   Annotated[str, email, skip_first]

Here it makes little difference, but the gain in efficiency may be important for larger schemas.

Let's check that validation also works with type annotations:

.. testcode::

   validate(book_schema, bad_book, name="bad_book")

.. testoutput::

   Traceback (most recent call last):
       ...
       raise ValidationError(message)
   vtjson.vtjson.ValidationError: bad_book is not of type 'book_schema': bad_book['authors'][0] is not of type 'person_schema': bad_book['authors'][0]['email'] (value:'margaret@gmailcom') is not of type 'email': The part after the @-sign is not valid. It should have a period.

Real world examples
-------------------

.. _example1:

Example 1
^^^^^^^^^

Below we give the schema of a recent version of the run object in the mongodb database underlying the Fishtest web application https://tests.stockfishchess.org/tests. For the latest version see https://raw.githubusercontent.com/official-stockfish/fishtest/master/server/fishtest/schemas.py.
See :ref:`example2` for a version of this example that is compatible with Python type annotations.

.. code-block :: python

  import copy
  import math
  from datetime import datetime, timezone

  from bson.objectid import ObjectId

  from vtjson import (
      at_most_one_of,
      div,
      fields,
      ge,
      glob,
      gt,
      ifthen,
      intersect,
      ip_address,
      keys,
      lax,
      one_of,
      quote,
      regex,
      set_name,
      union,
      url,
  )

  username = regex(r"[!-~][ -~]{0,30}[!-~]", name="username")
  net_name = regex("nn-[a-f0-9]{12}.nnue", name="net_name")
  tc = regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc")
  str_int = regex(r"[1-9]\d*", name="str_int")
  sha = regex(r"[a-f0-9]{40}", name="sha")
  country_code = regex(r"[A-Z][A-Z]", name="country_code")
  run_id = set_name(ObjectId.is_valid, "run_id")
  uuid = regex(r"[0-9a-zA-Z]{2,}(-[a-f0-9]{4}){3}-[a-f0-9]{12}", name="uuid")
  epd_file = glob("*.epd", name="epd_file")
  pgn_file = glob("*.pgn", name="pgn_file")
  even = div(2, name="even")
  datetime_utc = intersect(datetime, fields({"tzinfo": timezone.utc}))

  uint = intersect(int, ge(0))
  suint = intersect(int, gt(0))
  ufloat = intersect(float, ge(0))
  sufloat = intersect(float, gt(0))


  def valid_results(R):
      l, d, w = R["losses"], R["draws"], R["wins"]
      R = R["pentanomial"]
      return (
	  l + d + w == 2 * sum(R)
	  and w - l == 2 * R[4] + R[3] - R[1] - 2 * R[0]
	  and R[3] + 2 * R[2] + R[1] >= d >= R[3] + R[1]
      )


  zero_results = {
      "wins": 0,
      "draws": 0,
      "losses": 0,
      "crashes": 0,
      "time_losses": 0,
      "pentanomial": 5 * [0],
  }

  if_bad_then_zero_stats_and_not_active = ifthen(
      keys("bad"), lax({"active": False, "stats": quote(zero_results)})
  )


  def final_results_must_match(run):
      rr = copy.deepcopy(zero_results)
      for t in run["tasks"]:
	  r = t["stats"]
	  for k in r:
	      if k != "pentanomial":
		  rr[k] += r[k]
	      else:
		  for i, p in enumerate(r["pentanomial"]):
		      rr[k][i] += p
      if rr != run["results"]:
	  raise Exception(
	      f"The final results {run['results']} do not match the computed results {rr}"
	  )
      else:
	  return True


  def cores_must_match(run):
      cores = 0
      for t in run["tasks"]:
	  if t["active"]:
	      cores += t["worker_info"]["concurrency"]
      if cores != run["cores"]:
	  raise Exception(
	      f"Cores mismatch. Cores from tasks: {cores}. Cores from "
	      f"run: {run['cores']}"
	  )

      return True


  def workers_must_match(run):
      workers = 0
      for t in run["tasks"]:
	  if t["active"]:
	      workers += 1
      if workers != run["workers"]:
	  raise Exception(
	      f"Workers mismatch. Workers from tasks: {workers}. Workers from "
	      f"run: {run['workers']}"
	  )

      return True


  valid_aggregated_data = intersect(
      final_results_must_match,
      cores_must_match,
      workers_must_match,
  )

  worker_info_schema = {
      "uname": str,
      "architecture": [str, str],
      "concurrency": suint,
      "max_memory": uint,
      "min_threads": suint,
      "username": str,
      "version": uint,
      "python_version": [uint, uint, uint],
      "gcc_version": [uint, uint, uint],
      "compiler": union("clang++", "g++"),
      "unique_key": uuid,
      "modified": bool,
      "ARCH": str,
      "nps": ufloat,
      "near_github_api_limit": bool,
      "remote_addr": ip_address,
      "country_code": union(country_code, "?"),
  }

  results_schema = intersect(
      {
	  "wins": uint,
	  "losses": uint,
	  "draws": uint,
	  "crashes": uint,
	  "time_losses": uint,
	  "pentanomial": [uint, uint, uint, uint, uint],
      },
      valid_results,
  )

  runs_schema = intersect(
      {
	  "_id?": ObjectId,
	  "version": uint,
	  "start_time": datetime_utc,
	  "last_updated": datetime_utc,
	  "tc_base": ufloat,
	  "base_same_as_master": bool,
	  "rescheduled_from?": run_id,
	  "approved": bool,
	  "approver": union(username, ""),
	  "finished": bool,
	  "deleted": bool,
	  "failed": bool,
	  "is_green": bool,
	  "is_yellow": bool,
	  "workers": uint,
	  "cores": uint,
	  "results": results_schema,
	  "results_info?": {
	      "style": str,
	      "info": [str, ...],
	  },
	  "args": intersect(
	      {
		  "base_tag": str,
		  "new_tag": str,
		  "base_nets": [net_name, ...],
		  "new_nets": [net_name, ...],
		  "num_games": intersect(uint, even),
		  "tc": tc,
		  "new_tc": tc,
		  "book": union(epd_file, pgn_file),
		  "book_depth": str_int,
		  "threads": suint,
		  "resolved_base": sha,
		  "resolved_new": sha,
		  "master_sha": sha,
		  "official_master_sha": sha,
		  "msg_base": str,
		  "msg_new": str,
		  "base_options": str,
		  "new_options": str,
		  "info": str,
		  "base_signature": str_int,
		  "new_signature": str_int,
		  "username": username,
		  "tests_repo": url,
		  "auto_purge": bool,
		  "throughput": ufloat,
		  "itp": ufloat,
		  "priority": float,
		  "adjudication": bool,
		  "sprt?": intersect(
		      {
			  "alpha": 0.05,
			  "beta": 0.05,
			  "elo0": float,
			  "elo1": float,
			  "elo_model": "normalized",
			  "state": union("", "accepted", "rejected"),
			  "llr": float,
			  "batch_size": suint,
			  "lower_bound": -math.log(19),
			  "upper_bound": math.log(19),
			  "lost_samples?": uint,
			  "illegal_update?": uint,
			  "overshoot?": {
			      "last_update": uint,
			      "skipped_updates": uint,
			      "ref0": float,
			      "m0": float,
			      "sq0": ufloat,
			      "ref1": float,
			      "m1": float,
			      "sq1": ufloat,
			  },
		      },
		      one_of("overshoot", "lost_samples"),
		  ),
		  "spsa?": {
		      "A": ufloat,
		      "alpha": ufloat,
		      "gamma": ufloat,
		      "raw_params": str,
		      "iter": uint,
		      "num_iter": uint,
		      "params": [
			  {
			      "name": str,
			      "start": float,
			      "min": float,
			      "max": float,
			      "c_end": sufloat,
			      "r_end": ufloat,
			      "c": sufloat,
			      "a_end": ufloat,
			      "a": ufloat,
			      "theta": float,
			  },
			  ...,
		      ],
		      "param_history?": [
			  [
			      {"theta": float, "R": ufloat, "c": ufloat},
			      ...,
			  ],
			  ...,
		      ],
		  },
	      },
	      at_most_one_of("sprt", "spsa"),
	  ),
	  "tasks": [
	      intersect(
		  {
		      "num_games": intersect(uint, even),
		      "active": bool,
		      "last_updated": datetime_utc,
		      "start": uint,
		      "residual?": float,
		      "residual_color?": str,
		      "bad?": True,
		      "stats": results_schema,
		      "worker_info": worker_info_schema,
		  },
		  if_bad_then_zero_stats_and_not_active,
	      ),
	      ...,
	  ],
	  "bad_tasks?": [
	      {
		  "num_games": intersect(uint, even),
		  "active": False,
		  "last_updated": datetime_utc,
		  "start": uint,
		  "residual": float,
		  "residual_color": str,
		  "bad": True,
		  "task_id": uint,
		  "stats": results_schema,
		  "worker_info": worker_info_schema,
	      },
	      ...,
	  ],
      },
      lax(ifthen({"approved": True}, {"approver": username}, {"approver": ""})),
      lax(ifthen({"is_green": True}, {"is_yellow": False})),
      lax(ifthen({"is_yellow": True}, {"is_green": False})),
      lax(ifthen({"failed": True}, {"finished": True})),
      lax(ifthen({"deleted": True}, {"finished": True})),
      lax(ifthen({"finished": True}, {"workers": 0, "cores": 0})),
      lax(ifthen({"finished": True}, {"tasks": [{"active": False}, ...]})),
      valid_aggregated_data,
  )

.. _example2:

Example 2
^^^^^^^^^

This is a rewrite of :ref:`example1` that is compatible with Python type annotations.

.. code-block :: python

  import copy
  import math
  from datetime import datetime, timezone
  from typing import Annotated, Literal, NotRequired, TypedDict

  from bson.objectid import ObjectId

  from vtjson import (
      at_most_one_of,
      div,
      fields,
      ge,
      glob,
      gt,
      ifthen,
      intersect,
      ip_address,
      keys,
      lax,
      one_of,
      quote,
      regex,
      skip_first,
      url,
  )

  username = Annotated[str, regex(r"[!-~][ -~]{0,30}[!-~]", name="username"), skip_first]
  net_name = Annotated[str, regex("nn-[a-f0-9]{12}.nnue", name="net_name"), skip_first]
  tc = Annotated[
      str, regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc"), skip_first
  ]
  str_int = Annotated[str, regex(r"[1-9]\d*", name="str_int"), skip_first]
  sha = Annotated[str, regex(r"[a-f0-9]{40}", name="sha"), skip_first]
  country_code = Annotated[str, regex(r"[A-Z][A-Z]", name="country_code"), skip_first]
  run_id = Annotated[str, ObjectId.is_valid]
  uuid = Annotated[
      str,
      regex(r"[0-9a-zA-Z]{2,}(-[a-f0-9]{4}){3}-[a-f0-9]{12}", name="uuid"),
      skip_first,
  ]
  epd_file = Annotated[str, glob("*.epd", name="epd_file"), skip_first]
  pgn_file = Annotated[str, glob("*.pgn", name="pgn_file"), skip_first]
  even = Annotated[int, div(2, name="even"), skip_first]
  datetime_utc = Annotated[datetime, fields({"tzinfo": timezone.utc})]

  uint = Annotated[int, ge(0)]
  suint = Annotated[int, gt(0)]
  ufloat = Annotated[float, ge(0)]
  sufloat = Annotated[float, gt(0)]


  class results_type(TypedDict):
      wins: uint
      losses: uint
      draws: uint
      crashes: uint
      time_losses: uint
      pentanomial: Annotated[list[int], [uint, uint, uint, uint, uint], skip_first]


  def valid_results(R: results_type) -> bool:
      l, d, w = R["losses"], R["draws"], R["wins"]
      Rp = R["pentanomial"]
      return (
	  l + d + w == 2 * sum(Rp)
	  and w - l == 2 * Rp[4] + Rp[3] - Rp[1] - 2 * Rp[0]
	  and Rp[3] + 2 * Rp[2] + Rp[1] >= d >= Rp[3] + Rp[1]
      )


  results_schema = Annotated[
      results_type,
      valid_results,
  ]


  class worker_info_schema(TypedDict):
      uname: str
      architecture: Annotated[list[str], [str, str], skip_first]
      concurrency: suint
      max_memory: uint
      min_threads: suint
      username: str
      version: uint
      python_version: Annotated[list[int], [uint, uint, uint], skip_first]
      gcc_version: Annotated[list[int], [uint, uint, uint], skip_first]
      compiler: Literal["clang++", "g++"]
      unique_key: uuid
      modified: bool
      ARCH: str
      nps: ufloat
      near_github_api_limit: bool
      remote_addr: Annotated[str, ip_address]
      country_code: country_code | Literal["?"]


  class overshoot_type(TypedDict):
      last_update: uint
      skipped_updates: uint
      ref0: float
      m0: float
      sq0: ufloat
      ref1: float
      m1: float
      sq1: ufloat


  class sprt_type(TypedDict):
      alpha: Annotated[float, 0.05, skip_first]
      beta: Annotated[float, 0.05, skip_first]
      elo0: float
      elo1: float
      elo_model: Literal["normalized"]
      state: Literal["", "accepted", "rejected"]
      llr: float
      batch_size: suint
      lower_bound: Annotated[float, -math.log(19), skip_first]
      upper_bound: Annotated[float, math.log(19), skip_first]
      lost_samples: NotRequired[uint]
      illegal_update: NotRequired[uint]
      overshoot: NotRequired[overshoot_type]


  sprt_schema = Annotated[
      sprt_type,
      one_of("overshoot", "lost_samples"),
  ]


  class param_schema(TypedDict):
      name: str
      start: float
      min: float
      max: float
      c_end: sufloat
      r_end: ufloat
      c: sufloat
      a_end: ufloat
      a: ufloat
      theta: float


  class param_history_schema(TypedDict):
      theta: float
      R: ufloat
      c: ufloat


  class spsa_schema(TypedDict):
      A: ufloat
      alpha: ufloat
      gamma: ufloat
      raw_params: str
      iter: uint
      num_iter: uint
      params: list[param_schema]
      param_history: NotRequired[list[list[param_history_schema]]]


  class args_type(TypedDict):
      base_tag: str
      new_tag: str
      base_nets: list[net_name]
      new_nets: list[net_name]
      num_games: Annotated[uint, even]
      tc: tc
      new_tc: tc
      book: epd_file | pgn_file
      book_depth: str_int
      threads: suint
      resolved_base: sha
      resolved_new: sha
      master_sha: sha
      official_master_sha: sha
      msg_base: str
      msg_new: str
      base_options: str
      new_options: str
      info: str
      base_signature: str_int
      new_signature: str_int
      username: username
      tests_repo: Annotated[str, url, skip_first]
      auto_purge: bool
      throughput: ufloat
      itp: ufloat
      priority: float
      adjudication: bool
      sprt: NotRequired[sprt_schema]
      spsa: NotRequired[spsa_schema]


  args_schema = Annotated[
      args_type,
      at_most_one_of("sprt", "spsa"),
  ]


  class task_type(TypedDict):
      num_games: Annotated[uint, even]
      active: bool
      last_updated: datetime_utc
      start: uint
      residual: float
      residual_color: NotRequired[str]
      bad: NotRequired[Literal[True]]
      stats: results_schema
      worker_info: worker_info_schema


  zero_results: results_type = {
      "wins": 0,
      "draws": 0,
      "losses": 0,
      "crashes": 0,
      "time_losses": 0,
      "pentanomial": 5 * [0],
  }

  if_bad_then_zero_stats_and_not_active = ifthen(
      keys("bad"), lax({"active": False, "stats": quote(zero_results)})
  )

  task_schema = Annotated[
      task_type,
      if_bad_then_zero_stats_and_not_active,
  ]


  class bad_task_schema(TypedDict):
      num_games: Annotated[uint, even]
      active: Literal[False]
      last_updated: datetime_utc
      start: uint
      residual: float
      residual_color: str
      bad: Literal[True]
      task_id: uint
      stats: results_schema
      worker_info: worker_info_schema


  class results_info_schema(TypedDict):
      style: str
      info: list[str]


  class runs_type(TypedDict):
      _id: NotRequired[ObjectId]
      version: uint
      start_time: datetime_utc
      last_updated: datetime_utc
      tc_base: ufloat
      base_same_as_master: bool
      rescheduled_from: NotRequired[run_id]
      approved: bool
      approver: username | Literal[""]
      finished: bool
      deleted: bool
      failed: bool
      is_green: bool
      is_yellow: bool
      workers: uint
      cores: uint
      results: results_schema
      results_info: NotRequired[results_info_schema]
      args: args_schema
      tasks: list[task_schema]
      bad_tasks: NotRequired[list[bad_task_schema]]


  def final_results_must_match(run: runs_type) -> bool:
      rr = copy.deepcopy(zero_results)
      for t in run["tasks"]:
	  r = t["stats"]
	  # mypy does not support variable keys for
	  # TypedDict
	  rr["wins"] += r["wins"]
	  rr["losses"] += r["losses"]
	  rr["draws"] += r["draws"]
	  rr["crashes"] += r["crashes"]
	  rr["time_losses"] += r["time_losses"]
	  for i, p in enumerate(r["pentanomial"]):
	      rr["pentanomial"][i] += p
      if rr != run["results"]:
	  raise Exception(
	      f"The final results {run['results']} do not match the computed results {rr}"
	  )
      else:
	  return True


  def cores_must_match(run: runs_type) -> bool:
      cores = 0
      for t in run["tasks"]:
	  if t["active"]:
	      cores += t["worker_info"]["concurrency"]
      if cores != run["cores"]:
	  raise Exception(
	      f"Cores mismatch. Cores from tasks: {cores}. Cores from "
	      f"run: {run['cores']}"
	  )

      return True


  def workers_must_match(run: runs_type) -> bool:
      workers = 0
      for t in run["tasks"]:
	  if t["active"]:
	      workers += 1
      if workers != run["workers"]:
	  raise Exception(
	      f"Workers mismatch. Workers from tasks: {workers}. Workers from "
	      f"run: {run['workers']}"
	  )

      return True


  valid_aggregated_data = intersect(
      final_results_must_match,
      cores_must_match,
      workers_must_match,
  )

  runs_schema = Annotated[
      runs_type,
      lax(ifthen({"approved": True}, {"approver": username}, {"approver": ""})),
      lax(ifthen({"is_green": True}, {"is_yellow": False})),
      lax(ifthen({"is_yellow": True}, {"is_green": False})),
      lax(ifthen({"failed": True}, {"finished": True})),
      lax(ifthen({"deleted": True}, {"finished": True})),
      lax(ifthen({"finished": True}, {"workers": 0, "cores": 0})),
      lax(ifthen({"finished": True}, {"tasks": [{"active": False}, ...]})),
      valid_aggregated_data,
  ]





