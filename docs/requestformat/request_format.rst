.. module:: requestformat
.. _request_format: http://flask-restless.readthedocs.org/en/latest/requestformat.html#format-of-requests-and-responses

:mod:`request_format` -- Format of requests and responses
-----------------------------------------------------------------------

Responses are all in JSON format set with mimetype 'application/json'.
For requests that require a body (:http:method:`post`/:http:method:`post`/:http:method:`post`) ensure that you set a correctly Content-Type,
otherwise the server will responds with a :http:statuscode:`415`.
Tornado Restless supports in addition to ``Content-Type: application/json`` the ``Content-Type: application/x-www-url-encodeded`` format.

.. note::
 The x-www-url-encodeded format should be fine for basics, but due the lack of type information,
 Tornado Restless will do some implicit conversions that may not reflect the correct intention
 (e.g. a parameter with one element (?param=value) is always a string, a parameter with 2 or more values is a list (?param=value1&param=value2)).



