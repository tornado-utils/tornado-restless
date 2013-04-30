#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from collections import defaultdict
from json import loads
import logging
from math import ceil
from traceback import print_exception
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import object_mapper
from sqlalchemy.orm.exc import UnmappedInstanceError
from tornado.web import RequestHandler, HTTPError

from ..helper.IllegalArgumentError import IllegalArgumentError
from ..helper.ModelWrapper import SessionedModelWrapper

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '26.04.13 - 22:09'


class BaseHandler(RequestHandler):
    """
        Basic Blueprint for a sqlalchemy model
    """


    # noinspection PyMethodOverriding
    def initialize(self,
                   model,
                   session,
                   methods,
                   allow_patch_many,
                   validation_exceptions,
                   include_columns,
                   exclude_columns,
                   results_per_page,
                   max_results_per_page):
        """

        :param model: The Model for which this handler has been created
        :param methods:
        :param session:
        :param allow_patch_many:
        :param validation_exceptions:
        :param include_columns:
        :param exclude_columns:
        :param results_per_page:
        :param max_results_per_page:
        """
        super().initialize()

        self.model = SessionedModelWrapper(model, session)
        self.methods = [method.lower() for method in methods]
        self.allow_patch_many = allow_patch_many
        self.validation_exceptions = validation_exceptions

        self.results_per_page = results_per_page
        self.max_results_per_page = max_results_per_page

        self.include_columns, self.include_relations = self.parse_columns(include_columns)
        self.exclude_columns, self.exclude_relations = self.parse_columns(exclude_columns)

    def parse_columns(self, strings):

        columns = []
        relations = defaultdict(list)

        # Strings
        if strings is None:
            return None, None

        # Parse
        for column in [column.split(".", 1) for column in strings]:
            if len(column) == 1:
                columns.append(column[0])
            else:
                relations[column[0]].append(column[1])

        # Delete relations in columns
        for column in relations:
            if column in columns:
                columns.remove(column)

        # Now parse relations
        for (key, relation_columns) in relations.items():
            relations[key] = self.parse_columns(relation_columns)

        # Return
        return columns, relations

    def get_filters(self):
        """
            Returns a list of filters bade by the query argument
        """

        argument_filters = loads(self.get_argument("filters", "[]"))

        for argument_order in loads(self.get_argument("order_by", "[]")):
            direction = argument_order['direction']
            if direction not in ["asc", "desc"]:
                raise IllegalArgumentError("Direction unkown")
            argument_filters.append({'name': argument_order['field'], 'op': direction})

        alchemy_filters = []
        for argument_filter in argument_filters:

            left = getattr(self.model, argument_filter["name"])
            op = argument_filter["op"]

            if "field" in argument_filter.keys():
                right = getattr(self.model, argument_filter["field"])
            elif "val" in argument_filter.keys():
                right = argument_filter["val"]
            else:
                right = None

            # Operators from flask-restless
            if op in ["is_null"]:
                alchemy_filters.append(left.is_(None))
            elif op in ["is_not_null"]:
                alchemy_filters.append(left.isnot(None))
            elif op in ["is"]:
                alchemy_filters.append(left.is_(right))
            elif op in ["is_not"]:
                alchemy_filters.append(left.isnot(right))
            elif op in ["==", "eq", "equals", "equals_to"]:
                alchemy_filters.append(left == right)
            elif op in ["!=", "ne", "neq", "not_equal_to", "does_not_equal"]:
                alchemy_filters.append(left != right)
            elif op in [">", "gt"]:
                alchemy_filters.append(left > right)
            elif op in ["<", "lt"]:
                alchemy_filters.append(left < right)
            elif op in [">=", "ge", "gte", "geq"]:
                alchemy_filters.append(left >= right)
            elif op in ["<=", "le", "lte", "leq"]:
                alchemy_filters.append(left <= right)
            elif op in ["ilike"]:
                alchemy_filters.append(left.ilike(right))
            elif op in ["not_ilike"]:
                alchemy_filters.append(left.notilike(right))
            elif op in ["like"]:
                alchemy_filters.append(left.like(right))
            elif op in ["not_like"]:
                alchemy_filters.append(left.notlike(right))
            elif op in ["match"]:
                alchemy_filters.append(left.match(right))
            elif op in ["in"]:
                alchemy_filters.append(left.in_(right))
            elif op in ["not_in"]:
                alchemy_filters.append(left.notin_(right))
            elif op in ["has"]:
                alchemy_filters.append(left.has(right))
            elif op in ["any"]:
                alchemy_filters.append(left.any(right))

            # Additional Operators
            if op in ["between"]:
                alchemy_filters.append(left.between(*right))
            elif op in ["contains"]:
                alchemy_filters.append(left.contains(right))
            elif op in ["startswith"]:
                alchemy_filters.append(left.startswith(right))
            elif op in ["endswith"]:
                alchemy_filters.append(left.endswith(right))

            # Order By Operators
            if op in ["asc"]:
                alchemy_filters.append(left.asc())
            elif op in ["desc"]:
                alchemy_filters.append(left.asc())
        return alchemy_filters


    def write_error(self, status_code: int, **kwargs):
        """
            Encodes any exceptions thrown to json

            SQLAlchemyError will be encoded as 400 / SQLAlchemy: Bad Request
            Errors from the restless api as 400 / Restless: Bad Arguments
            Any other exceptions will occur as an 500 exception

            :param status_code: The Status Code in Response
        """

        if 'exc_info' in kwargs:
            exc_type, exc_value = kwargs['exc_info'][:2]
            print_exception(*kwargs['exc_info'])
            if issubclass(exc_type, HTTPError) and exc_value.reason:
                self.set_status(status_code, reason=exc_value.reason)
            elif issubclass(exc_type, SQLAlchemyError):
                self.set_status(400, reason='SQLAlchemy: Bad Request')
            elif issubclass(exc_type, IllegalArgumentError):
                self.set_status(400, reason='Restless: Bad Arguments')
            self.finish({'type': exc_type.__name__, 'message': "%s" % exc_value})
        else:
            super().write_error(status_code, **kwargs)


    def get(self, pks=None):
        """
            GET request
        """

        if not 'get' in self.methods:
            self.send_error(405)
            return

        if pks is None:
            self.get_all()
        else:
            self.get_one(pks)

    def get_one(self, pks):
        """
            Get one instance with primary_keys pks
        """

        # Get Instance
        instance = self.model.get(pks.split(","))

        # To Dict
        self.write(self.to_dict(instance,
                                include_columns=self.include_columns,
                                include_relations=self.include_relations))

    def get_all(self):
        """
            Get all instances
        """

        # Results per Page
        results_per_page = self.get_argument("results_per_page", self.results_per_page)
        if results_per_page > self.max_results_per_page:
            raise IllegalArgumentError("request.results_per_page > application.max_results_per_page")

        # Offset
        offset = self.get_argument("offset", 0)
        page = self.get_argument("page", 1) - 1
        offset += page * results_per_page
        if offset < 0:
            raise IllegalArgumentError("request.offset < 0")

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_argument("limit", results_per_page)

        # Num Results
        num_results = self.model.count(filters=filters)
        num_pages = ceil(num_results / results_per_page)

        # Get Instances
        instances = self.model.all(offset=offset, limit=limit, filters=filters)

        self.write({'num_results': num_results,
                    "num_pages": num_pages,
                    "page": page + 1,
                    "objects": self.to_dict(instances,
                                            include_columns=self.include_columns,
                                            include_relations=self.include_relations)})

    def to_dict(self, instance,
                include_columns=None,
                include_relations=None,
                exclude_columns=None,
                exclude_relations=None):
        """
            Translates sqlalchemy instance to dictionary

            Inspired by flask-restless.helpers.to_dict

            :param instance:
            :param include_columns: Columns that should be included for an instance
            :param include_relations: Relations that should be include for an instance
            :param exclude_columns: Columns that should not be included for an instance
            :param exclude_relations: Relations that should not be include for an instance
        """

        # None
        if instance is None:
            return None

        # List
        if isinstance(instance, list):
            return [self.to_dict(x) for x in instance]

        # Dictionary
        if isinstance(instance, dict):
            return {k: self.to_dict(v) for k, v in instance.items()}

        # Int
        if isinstance(instance, int):
            return instance

        # String
        if isinstance(instance, str):
            return instance

        # Any Dictionary Object
        if hasattr(instance, 'items'):
            return {k: self.to_dict(v) for k, v in instance.items()}

        # Include Columns given
        if include_columns is not None:
            rtn = {}
            for column in include_columns:
                rtn[column] = self.to_dict(getattr(instance, column))
            for (column, include_relation) in include_relations.items():
                rtn[column] = self.to_dict(getattr(instance, column),
                                           include_columns=include_relations[0],
                                           include_relations=include_relations[1])
            return rtn

        if exclude_columns is None:
            exclude_columns = []

        if exclude_relations is None:
            exclude_relations = {}

        # SQLAlchemy instance?
        try:
            include_columns = [p.key for p in self.model.get_columns(object_mapper(instance))]
            include_relations = [p.key for p in self.model.get_relations(object_mapper(instance))]
            include_proxies = [p.key for p in self.model.get_proxies(object_mapper(instance))]
            include_hybrids = [p.key for p in self.model.get_hybrids(object_mapper(instance))]

            rtn = {}

            # Include Columns
            for column in include_columns:
                if not column in exclude_columns:
                    rtn[column] = self.to_dict(getattr(instance, column))

            # Include AssociationProxy
            for column in include_proxies:
                if not column in exclude_columns:
                    try:
                        rtn[column] = self.to_dict(getattr(instance, column))
                    except AttributeError:
                        rtn[column] = None

            # Include Hybrid Properties
            for column in include_hybrids:
                if not column in exclude_columns:
                    rtn[column] = self.to_dict(getattr(instance, column))

            # Include Relations but only one deep
            for column in include_relations:
                if exclude_relations is not None and column in exclude_relations:
                    continue
                if include_relations is None or column in include_relations:
                    rtn[column] = self.to_dict(getattr(instance, column), include_relations=[])

            return rtn
        except UnmappedInstanceError:
            self.logger.info("Possible unkown instance type: %s" % type(instance))
            return instance

    @property
    def logger(self):
        """
            Get the Request Logger
        """
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger('tornado.restless')
        return self._logger







