.. module:: searchformat
.. _query_format: http://flask-restless.readthedocs.org/en/latest/searchformat.html#query-format

:mod:`query_format` -- Query Format
------------------------------------------------

The Query format is the same as in Flask Restless, see query_format_.

In addition <ou can specify for the order_by operators asc and desc a nullsfirst and nullslast argument,
emitting an ASC NULLS LAST or NULLS FIRST respectivly.

Likewise Flask Restless, Tornado Restless responds with 404 [Restless: Bad Arguments] if the filter is poorly formated.
If it is not an obvious error, 404 [SQLAlchemy: Bad Arguments] may be raised.