#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""
    Tornado Restless BaseHandler

    Handles all registered blueprints, you may override this class and
     use the modification via create_api_blueprint(handler_class=...)
"""
from collections import defaultdict
from json import loads
import logging
from math import ceil
from traceback import print_exception
from urllib.parse import parse_qs
import sys

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import UnmappedInstanceError
from tornado.web import RequestHandler, HTTPError
from tornado_restless.helper.DictConverter import to_dict


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

from ..helper.IllegalArgumentError import IllegalArgumentError
from ..helper.ModelWrapper import SessionedModelWrapper

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '26.04.13 - 22:09'


class BaseHandler(RequestHandler):
    """
        Basic Blueprint for a sqlalchemy model
    """

    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    # noinspection PyMethodOverriding
    def initialize(self,
                   model,
                   session,
                   methods,
                   allow_patch_many,
                   allow_method_override,
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
        :param allow_method_override:
        :param validation_exceptions:
        :param include_columns:
        :param exclude_columns:
        :param results_per_page:
        :param max_results_per_page:
        """

        # Override Method if Header provided
        if allow_method_override and 'X-HTTP-Method-Override' in self.request.headers:
            self.request.method = self.request.headers['X-HTTP-Method-Override']

        super().initialize()

        self.model = SessionedModelWrapper(model, session)
        self.methods = [method.lower() for method in methods]
        self.allow_patch_many = allow_patch_many
        self.validation_exceptions = validation_exceptions

        self.results_per_page = results_per_page
        self.max_results_per_page = max_results_per_page

        self.include_columns, self.include_relations = self.parse_columns(include_columns)
        self.exclude_columns, self.exclude_relations = self.parse_columns(exclude_columns)

    def parse_columns(self, strings: list):
        """
            Parse a list of column names (name1, name2, relation.name1, ...)

            :param strings: List of Column Names
            :return:
        """
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

        # Get all provided filters
        argument_filters = self.get_query_argument("filters", [])

        # Parse order by as filters
        argument_orders = self.get_query_argument("order_by", [])
        for argument_order in argument_orders:
            direction = argument_order['direction']
            if direction not in ["asc", "desc"]:
                raise IllegalArgumentError("Direction unkown")
            argument_filters.append({'name': argument_order['field'], 'op': direction})

        # Create Alchemy Filters
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
            :param kwargs: Additional Parameters
        """

        if 'exc_info' in kwargs:
            exc_type, exc_value = kwargs['exc_info'][:2]
            print_exception(*kwargs['exc_info'])
            if issubclass(exc_type, HTTPError) and exc_value.reason:
                self.set_status(status_code, reason=exc_value.reason)
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value, **exc_value.__dict__))
            elif issubclass(exc_type, SQLAlchemyError):
                self.set_status(400, reason='SQLAlchemy: Bad Request')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, IllegalArgumentError):
                self.set_status(400, reason='Restless: Bad Arguments')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
        else:
            super().write_error(status_code, **kwargs)

    def patch(self, pks=None):
        """
            PATCH (update instance) request

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        if not 'patch' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        if pks is None:
            if self.allow_patch_many:
                self.patch_many()
            else:
                self.send_error(403)
        else:
            self.patch_single(pks)

    def patch_many(self):
        """
            Patch many instances
        """

        # Flush
        self.model.session.flush()

        # Get values
        values = self.get_argument_values()

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_query_argument("limit", None)

        # Modify Instances
        if self.get_query_argument("single", False):
            instance = self.model.one(filters=filters)
            for (key, value) in values.items():
                logging.debug("%s => %s" % (key, value))
                setattr(instance, key, value)
            num = 1
        else:
            num = self.model.update(values, limit=limit, filters=filters)

        # Commit
        self.model.session.commit()

        # Result
        self.set_status(200, "Removed")
        self.write({'num_removed': num})

    def patch_single(self, pks: str):
        """
            Patch one instance with primary_keys pks

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        # Flush
        self.model.session.flush()

        # Get values
        values = self.get_argument_values()

        # Get Instance
        instance = self.model.get(pks.split(","))
        for (key, value) in values.items():
            logging.debug("%s => %s" % (key, value))
            setattr(instance, key, value)

        # Commit
        self.model.session.commit()

        # Refresh
        self.model.session.refresh(instance)

        # Result
        self.set_status(201, "Patched")
        self.write(self.to_dict(instance,
                                include_columns=self.include_columns,
                                include_relations=self.include_relations,
                                exclude_columns=self.exclude_columns,
                                exclude_relations=self.exclude_relations))

    def delete(self, pks=None):
        """
            DELETE (delete instance) request

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        if not 'delete' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        if pks is None:
            if self.allow_patch_many:
                self.delete_many()
            else:
                self.send_error(403)
        else:
            self.delete_single(pks)

    def delete_many(self):
        """
            Remove many instances
        """

        # Flush
        self.model.session.flush()

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_query_argument("limit", None)

        # Modify Instances
        if self.get_query_argument("single", False):
            instance = self.model.one(filters=filters)
            self.model.session.delete(instance)
            self.model.session.commit()
            num = 1
        else:
            num = self.model.delete(limit=limit, filters=filters)

        # Commit
        self.model.session.commit()

        # Result
        self.set_status(200, "Removed")
        self.write({'num_removed': num})

    def delete_single(self, pks):
        """
            Get one instance with primary_keys pks

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        # Get Instance
        instance = self.model.get(pks.split(","))

        # Trigger deletion
        self.model.session.delete(instance)
        self.model.session.commit()

        # Status
        self.set_status(204, "Instance removed")

    def put(self, pks=None):
        """
            PUT (update instance) request

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        if not 'put' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        if pks is None:
            if self.allow_patch_many:
                self.patch_many()
            else:
                self.send_error(403)
        else:
            self.patch_single(pks)

    def post(self, pks=None):
        """
            POST (new input) request

            :param pks: (ignored)
        """

        if not 'post' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        try:
            commit_exception = None

            with self.model.session.begin_nested():
                values = self.get_argument_values()

                # Create Instance
                instance = self.model(**values)

                # Commit
                try:
                    self.model.session.commit()
                except SQLAlchemyError:
                    self.model.session.rollback()
                    self.send_error(status_code=400, exc_info=sys.exc_info())
                    return

                # Refresh
                self.model.session.refresh(instance)

                # Set Status
                self.set_status(201)

                # To Dict
                self.write(self.to_dict(instance,
                                        include_columns=self.include_columns,
                                        include_relations=self.include_relations,
                                        exclude_columns=self.exclude_columns,
                                        exclude_relations=self.exclude_relations))
        except SQLAlchemyError as ex:
            logging.error(ex)
            self.model.session.rollback()

    def get_content_encoding(self):
        """
        Get the encoding the client sends us for encoding request.body correctly
        """

        content_type_args = {k.strip(): v for k, v in parse_qs(self.request.headers['Content-Type']).items()}
        if 'charset' in content_type_args and content_type_args['charset']:
            return content_type_args['charset'][0]
        else:
            return 'latin1'

    def get_body_arguments(self):
        """
            Get arguments encode as json body
        """

        try:
            return self._body_arguments
        except AttributeError:
            self.logger.info(self.request.body)
            self._body_arguments = loads(str(self.request.body, encoding=self.get_content_encoding()))
            return self._body_arguments

    def get_body_argument(self, name: str, default=RequestHandler._ARG_DEFAULT):
        """
        Get an argument named key from json encoded body

        :param name:
        :param default:
        :return:
        :raise: 400 Missing Argument
        """
        arguments = self.get_body_arguments()
        if name in arguments:
            return arguments[name]
        elif default is RequestHandler._ARG_DEFAULT:
            raise HTTPError(400, "Missing argument %s" % name)
        else:
            return default

    def get_query_argument(self, name: str, default=RequestHandler._ARG_DEFAULT):
        """
        Get an argument named key from json encoded body

        :param name:
        :param default:
        :return:
        :raise: 400 Missing Argument
        """

        try:
            query = self._query
        except AttributeError:
            query = self._query = loads(self.get_argument("q", default="{}"))

        if name in query:
            return query[name]
        elif default is RequestHandler._ARG_DEFAULT:
            raise HTTPError(400, "Missing argument %s" % name)
        else:
            return default

    def get_argument(self, name: str, *args, **kwargs):
        """
            On PUT/PATCH many request parameter may be located in body instead of query

            :param name: Name of argument
            :param kwargs: Additional parameters @see tornado.web.RequestHandler.get_argument
        """
        try:
            return super().get_argument(name, *args, **kwargs)
        except HTTPError:
            if name == "q" and self.request.method in ['PUT', 'PATCH']:
                return self.get_body_argument(name, *args, **kwargs)
            else:
                raise

    def get_argument_values(self):
        """
            Get all values provided via arguments
        """

        # Include Columns
        if self.include_columns is not None:
            values = {k: self.get_body_argument(k) for k in self.include_columns}
        else:
            values = {k: v for k, v in self.get_body_arguments().items()}

        # Exclude "q"
        if "q" in values:
            del values["q"]

        # Exclude Columns
        if self.exclude_columns is not None:
            for column in self.exclude_columns:
                if column in values:
                    del values[column]

        # Silently Ignore proxies
        for proxy in self.model.proxies:
            if proxy.key in values:
                self.logger.debug("Skipping proxy: %s" % proxy.key)
                del values[proxy.key]

        # Silently Ignore hybrids
        for hybrid in self.model.hybrids:
            if hybrid.key in values:
                self.logger.debug("Skipping hybrid: %s" % hybrid.key)
                del values[hybrid.key]

        # Handle Relations extra
        values_relations = {}
        for relation in self.model.relations:
            if relation.key in values:
                values_relations[relation.key] = values[relation.key]
                del values[relation.key]

        # Check Columns
        #for column in values:
        #    if not column in self.model.column_names:
        #        raise IllegalArgumentError("Column '%s' not defined for model %s" % (column, self.model.model))

        return values

    def patch_many(self):
        """
            Patch many instances
        """

        # Flush
        self.model.session.flush()

        # Get values
        values = self.get_argument_values()

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_query_argument("limit", None)

        # Modify Instances
        if self.get_query_argument("single", False):
            instances = [self.model.one(filters=filters)]
            for instance in instances:
                for (key, value) in values.items():
                    logging.debug("%s => %s" % (key, value))
                    setattr(instance, key, value)
            num = 1
        else:
            num = self.model.update(values, limit=limit, filters=filters)

        # Commit
        self.model.session.commit()

        # Result
        self.set_status(201, "Patched")
        self.write({'num_modified': num})

    def get(self, pks=None):
        """
            GET request

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        if not 'get' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        if pks is None:
            self.get_many()
        else:
            self.get_single(pks)

    def get_single(self, pks: str):
        """
            Get one instance with primary_keys pks

            :param pks: query argument of request (list of primary keys, comma seperated)
        """

        # Get Instance
        instance = self.model.get(pks.split(","))

        # To Dict
        self.write(self.to_dict(instance,
                                include_columns=self.include_columns,
                                include_relations=self.include_relations,
                                exclude_columns=self.exclude_columns,
                                exclude_relations=self.exclude_relations))

    def get_many(self):
        """
            Get all instances
        """

        # Results per Page
        results_per_page = self.get_query_argument("results_per_page", self.results_per_page)
        if results_per_page > self.max_results_per_page:
            raise IllegalArgumentError("request.results_per_page > application.max_results_per_page")

        # Offset
        offset = self.get_query_argument("offset", 0)
        page = self.get_query_argument("page", 1) - 1
        offset += page * results_per_page
        if offset < 0:
            raise IllegalArgumentError("request.offset < 0")

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_query_argument("limit", results_per_page)

        # Num Results
        num_results = self.model.count(filters=filters)
        num_pages = ceil(num_results / results_per_page)

        # Get Instances
        if self.get_query_argument("single", False):
            instances = [self.model.one(offset=offset, filters=filters)]
        else:
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
        try:
            return to_dict(instance=instance,
                           include_columns=include_columns, include_relations=include_relations,
                           exclude_columns=exclude_columns, exclude_relations=exclude_relations)
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