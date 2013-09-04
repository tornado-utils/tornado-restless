#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
import json
from tests.base import TestBase

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '04.09.13 - 16:14'


class TestGet(TestBase):
    """
        Test the result of some /post operations
    """

    def test_payload_format(self):
        """
            Test for raising 415
        """

        payload = {'_user': 3, 'cpu': 13.37, 'ram': 13.37}
        self.curl_tornado('/api/computers', 'post',
                          headers={'content-type': 'application/json'},
                          data=json.dumps(payload),
                          assert_for=201)
        self.curl_tornado('/api/computers', 'post',
                          headers={'content-type': 'application/x-www-form-urlencoded'},
                          data=payload,
                          assert_for=201)
        self.curl_tornado('/api/computers', 'post',
                          headers={'content-type': 'application/x-duck-typed'},
                          data="quak quak quak",
                          assert_for=415)

    def test_method(self):
        """
            Test for raising 405
        """

        payload = {'name': 'Jules'}
        self.curl_tornado('/api/cities', 'post',
                          data=payload,
                          assert_for=405)

