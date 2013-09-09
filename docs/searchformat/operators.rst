.. module:: searchformat
.. _query_format: http://flask-restless.readthedocs.org/en/latest/searchformat.html#operators

:mod:`operators` -- Operators
------------------------------------------

The operators strings recognized by the API include all the operators from Flask Restless
and some extensions:

  *   ==, eq, equals, equals_to
  *   !=, *ne*, neq, does_not_equal, not_equal_to
  *   >, gt, <, lt
  *   >=, ge, gte, geq, <=, le, lte, leq
  *   in, not_in
  *   is_null, is_not_null
  *   *is*, *is_not*
  *   like, *ilike*, *not_like*, *not_ilike*
  *   has
  *   any
  *   *match*, *between*, *containts*, *startswith*, *endswith*