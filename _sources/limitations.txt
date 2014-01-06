.. module:: limitations

:mod:`limitations` -- Limitations and Differences
-------------------------------------------------

Tornado Restless aims to be compilant with Flask-Restless but is currently still in development.
Some of known major differences are:

* No support for flask-sqlalchemy

Known differences that are planned to be supported in future:

* Capturing validation errors
* Request preprocessors and postprocessors (beside of extending the BaseHandler class for requests)
* Authentification support (beside of extending the BaseHandler class for request)

Known differences that may be supported in future:

* allow_functions keyword is unsupported
* JSONP callback keyword is unsupported

Minor differences:

* More operators are supported
* There are two differences :http:statuscode:`404` Bad Arguments exceptions either from the restless engine or the sqlalchemy engine
* Data modification may be passed via ``Content-Type: application/x-www-url-encodeded``
* The method_single processors accepts a list of primary_keys as arguments in difference to flask-restless where only one primary key is allowed.