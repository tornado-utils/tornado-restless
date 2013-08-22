#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""
    
"""
import logging
from .base import TestBase

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '21.08.13'


class TestGet(TestBase):
    """
        Test the result of some /get operations
    """

    def test_empty(self):
        """
            Test an empty query
        """

        flask_data = self.curl_flask('/api/persons')
        tornado_data = self.curl_tornado('/api/persons')

        logging.debug(flask_data)
        logging.debug(tornado_data)

        self.subsetOf(flask_data, tornado_data)

    def test_single(self):
        flask_data = self.curl_flask('/api/persons/1')
        tornado_data = self.curl_tornado('/api/persons/1')

        logging.debug(flask_data)
        logging.debug(tornado_data)

        self.subsetOf(flask_data, tornado_data)