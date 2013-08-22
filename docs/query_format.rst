.. module:: searchformat
.. _query_format: http://flask-restless.readthedocs.org/en/latest/searchformat.html#query-format

:mod:`searchformat.query_format` -- Query Format
------------------------------------------------

The Query format is the same as in Flask Restless, see query_format_.

Likewise Flask Restless, Tornado Restless responds with 404 [Restless: Bad Arguments] if the filter is poorly formated.
If it is not an obvious error, 404 [SQLAlchemy: Bad Arguments] may be raised.