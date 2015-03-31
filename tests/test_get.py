#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""
    
"""
import json
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

        assert self.subsetOf(flask_data, tornado_data)

    def test_likefilter(self):
        """
            Test like something
        """

        filters = [dict(name='name', op='like', val='%r%')]
        params = dict(q=json.dumps(dict(filters=filters)))

        flask_data = self.curl_flask('/api/persons', params=params)
        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(flask_data)
        logging.debug(tornado_data)

        assert self.subsetOf(flask_data, tornado_data)

        assert len(flask_data['objects']) == len(tornado_data['objects']) == 2
        assert flask_data['num_results'] == tornado_data['num_results'] == 2

    def test_ascsorting(self):
        """
            Test sorting (ascending)
        """

        order_by = [dict(field='age', direction='asc')]
        params = dict(q=json.dumps(dict(order_by=order_by)))

        flask_data = self.curl_flask('/api/persons', params=params)
        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(flask_data)
        logging.debug(tornado_data)

        assert self.subsetOf(flask_data, tornado_data)

        flask_ages = [o['age'] for o in flask_data['objects']]
        tornado_ages = [o['age'] for o in tornado_data['objects']]

        assert int(flask_ages[0]) == int(tornado_ages[0]) == 10
        assert int(flask_ages[1]) == int(tornado_ages[1]) == 14
        assert int(flask_ages[2]) == int(tornado_ages[2]) == 20

    def test_descsorting(self):
        """
            Test sorting (desscending)
        """

        order_by = [dict(field='age', direction='desc')]
        params = dict(q=json.dumps(dict(order_by=order_by)))

        flask_data = self.curl_flask('/api/persons', params=params)
        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(flask_data)
        logging.debug(tornado_data)

        assert self.subsetOf(flask_data, tornado_data)

        flask_ages = [o['age'] for o in flask_data['objects']]
        tornado_ages = [o['age'] for o in tornado_data['objects']]

        assert int(flask_ages[-1]) == int(tornado_ages[-1]) == 10
        assert int(flask_ages[-2]) == int(tornado_ages[-2]) == 14
        assert int(flask_ages[-3]) == int(tornado_ages[-3]) == 20

    def test_single(self):
        """
            Test for a specific persons per pk
        """

        flask_data = self.curl_flask('/api/persons/1')
        tornado_data = self.curl_tornado('/api/persons/1')

        logging.debug(flask_data)
        logging.debug(tornado_data)

        assert self.subsetOf(flask_data, tornado_data)

    def test_float(self):
        """
            Test for a float value
        """

        flask_data = self.curl_flask('/api/computers')
        tornado_data = self.curl_tornado('/api/computers')

        logging.debug(flask_data)
        logging.debug(tornado_data)

        assert self.subsetOf(flask_data, tornado_data)

        flask_computer_cpu = flask_data['objects'][0]['cpu']
        tornado_computer_cpu = tornado_data['objects'][0]['cpu']

        assert flask_computer_cpu == tornado_computer_cpu
        assert isinstance(tornado_computer_cpu, float)

    def test_results_per_page(self):
        """
            Test acknowledgment of parameter results_per_page
        """

        params = dict(results_per_page=2)

        flask_data = self.curl_flask('/api/persons', params=params)
        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(flask_data)
        logging.debug(tornado_data)

        assert self.subsetOf(flask_data, tornado_data)
        assert len(flask_data['objects']) == 2 == len(tornado_data['objects'])

    def test_nothing(self):
        """
            Test for some missing data
        """

        self.curl_tornado('/api/persons/1337', assert_for=400)

    def test_relation(self):
        params = {
            'q': json.dumps({'filters': [{'name': 'cities._city', 'op': 'any', 'val': 60400}]})
        }
        tornado_data = self.curl_tornado('/api/persons', params=params)
        assert len(tornado_data['objects']) == 2

        params = {
            'q': json.dumps({'filters': [{'name': 'cities._city', 'op': 'any', 'val': 10800}]})
        }
        tornado_data = self.curl_tornado('/api/persons', params=params)
        assert len(tornado_data['objects']) == 1

        params = {
            'q': json.dumps({'filters': [{'name': 'cities._city', 'op': 'any', 'val': 123}]})
        }
        tornado_data = self.curl_tornado('/api/persons', params=params)
        assert len(tornado_data['objects']) == 0
