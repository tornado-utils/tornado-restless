#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '22.08.13 - 17:44'

from tornado.web import HTTPError


class IllegalArgumentError(ValueError, HTTPError):
    """An exception occuring when there was a problem in parsing arguments or model data
    """

    def __init__(self, status_code=400, log_message=None, *args, **kwargs):
        super().__init__(status_code, log_message, *args, **kwargs)


try:
    from tornado.web import MethodNotAllowedError
except ImportError:
    class MethodNotAllowedError(HTTPError):
        """An exception occuring when the method is not supported by the handler

        Takes in addition to `HTTPError` arguments method and stores it value

        :arg string method: The name of the method that was called
        """

        def __init__(self, method=None, status_code=405, log_message=None, *args, **kwargs):
            super().__init__(status_code, log_message, *args, **kwargs)
            self.method = method