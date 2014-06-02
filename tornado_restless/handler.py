#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""
    Tornado Restless BaseHandler

    Handles all registered blueprints, you may override this class and
     use the modification via create_api_blueprint(handler_class=...)
"""
import inspect
from json import loads
import logging
from math import ceil
from traceback import print_exception
from urllib.parse import parse_qs
import sys
import itertools

from sqlalchemy import inspect as sqinspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.util import memoized_instancemethod, memoized_property
from tornado.web import RequestHandler, HTTPError

from .convert import to_dict, to_filter
from .errors import IllegalArgumentError, MethodNotAllowedError, ProcessingException
from .wrapper import SessionedModelWrapper


__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '26.04.13 - 22:09'


class BaseHandler(RequestHandler):
    """
        Basic Blueprint for a sqlalchemy model

        Subclass of :class:`tornado.web.RequestHandler` that handles web requests.

        Overwrite :func:`get() <get>` / :func:`post() <post>` / :func:`put() <put>` /
        :func:`patch() <patch>` / :func:`delete() <delete>` if you want complete customize handling of the methods.
        Note that the default implementation of this function check for the allowness and then call depending on
        the instance_id parameter the associated _single / _many method, so you probably want to call super()

        If you just want to customize the handling of the methods overwrite method_single or method_many.

        If you want completly disable a method overwrite the SUPPORTED_METHODS constant
    """

    ID_SEPARATOR = ","
    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    # noinspection PyMethodOverriding
    def initialize(self,
                   model,
                   manager,
                   methods: set,
                   preprocessor: dict,
                   postprocessor: dict,
                   allow_patch_many: bool,
                   allow_method_override: bool,
                   validation_exceptions,
                   exclude_queries: bool,
                   exclude_hybrids: bool,
                   include_columns: list,
                   exclude_columns: list,
                   results_per_page: int,
                   max_results_per_page: int):
        """

        Init of the handler, derives arguments from api create_api_blueprint

        :param model: The sqlalchemy model
        :param manager: The tornado_restless Api Manager
        :param methods: Allowed methods for this model
        :param preprocessor: A dictionary of preprocessor functions
        :param postprocessor: A dictionary of postprocessor functions
        :param allow_patch_many: Allow PATCH with multiple datasets
        :param allow_method_override: Support X-HTTP-Method-Override Header
        :param validation_exceptions:
        :param exclude_queries: Don't execude dynamic queries (like from associations or lazy relations)
        :param exclude_hybrids: When exclude_queries is True and exclude_hybrids is False, hybrids are still included.
        :param include_columns: Whitelist of columns to be included
        :param exclude_columns: Blacklist of columns to be excluded
        :param results_per_page: The default value of how many results are returned per request
        :param max_results_per_page: The hard upper limit of resutest per page

        :reqheader X-HTTP-Method-Override: If allow_method_override is True, this header overwrites the request method
        """

        # Override Method if Header provided
        if allow_method_override and 'X-HTTP-Method-Override' in self.request.headers:
            self.request.method = self.request.headers['X-HTTP-Method-Override']

        super(BaseHandler, self).initialize()

        self.model = SessionedModelWrapper(model, manager.session_maker())
        self.pk_length = len(sqinspect(model).primary_key)
        self.methods = [method.lower() for method in methods]
        self.allow_patch_many = allow_patch_many
        self.validation_exceptions = validation_exceptions

        self.preprocessor = preprocessor
        self.postprocessor = postprocessor

        self.results_per_page = results_per_page
        self.max_results_per_page = max_results_per_page

        self.include = self.parse_columns(include_columns)
        self.exclude = self.parse_columns(exclude_columns)

        self.to_dict_options = {'execute_queries': not exclude_queries, 'execute_hybrids': not exclude_hybrids}

    def prepare(self):
        """
            Prepare the request
        """
        self._call_preprocessor()

    def on_finish(self):
        """
            Finish the request
        """
        self._call_postprocessor()

    def parse_columns(self, strings: list) -> dict:
        """
            Parse a list of column names (name1, name2, relation.name1, ...)

            :param strings: List of Column Names
            :return:
        """
        columns = {}

        # Strings
        if strings is None:
            return None

        # Parse
        for column in [column.split(".", 1) for column in strings]:
            if len(column) == 1:
                columns[column[0]] = True
            else:
                columns.setdefault(column[0], []).append(column[1])

        # Now parse relations
        for (key, item) in columns.items():
            if isinstance(item, list):
                columns[key] = itertools.chain.from_iterable(self.parse_columns(strings) for strings in item)

        # Return
        return columns

    def get_filters(self):
        """
            Returns a list of filters made by the query argument

            :query filters: list of filters
            :query order_by: list of orderings
        """

        # Get all provided filters
        argument_filters = self.get_query_argument("filters", [])

        # Get all provided orders
        argument_orders = self.get_query_argument("order_by", [])

        return to_filter(self.model.model, argument_filters, argument_orders)

    def write_error(self, status_code: int, **kwargs):
        """
            Encodes any exceptions thrown to json

            SQLAlchemyError will be encoded as 400 / SQLAlchemy: Bad Request
            Errors from the restless api as 400 / Restless: Bad Arguments
            ProcessingException will be encoded with status code / ProcessingException: Stopped Processing
            Any other exceptions will occur as an 500 exception

            :param status_code: The Status Code in Response
            :param kwargs: Additional Parameters
        """
        if 'exc_info' in kwargs:
            exc_type, exc_value = kwargs['exc_info'][:2]
            if status_code >= 300:
                print_exception(*kwargs['exc_info'])
            if issubclass(exc_type, UnmappedInstanceError):
                self.set_status(400, reason='SQLAlchemy: Unmapped Instance')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, SQLAlchemyError):
                self.set_status(400, reason='SQLAlchemy: Bad Request')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, IllegalArgumentError):
                self.set_status(400, reason='Restless: Bad Arguments')
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, ProcessingException):
                self.set_status(status_code,
                                reason='ProcessingException: %s' % (exc_value.reason or "Stopped Processing"))
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value))
            elif issubclass(exc_type, HTTPError) and exc_value.reason:
                self.set_status(status_code, reason=exc_value.reason)
                self.finish(dict(type=exc_type.__module__ + "." + exc_type.__name__,
                                 message="%s" % exc_value, **exc_value.__dict__))
            else:
                super().write_error(status_code, **kwargs)
        else:
            super().write_error(status_code, **kwargs)

    def patch(self, instance_id: str=None):
        """
            PATCH (update instance) request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 403: PATCH MANY disallowed
            :statuscode 405: PATCH disallowed
        """

        if not 'patch' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        self._call_preprocessor(search_params=self.search_params)

        if instance_id is None:
            if self.allow_patch_many:
                result = self.patch_many()
            else:
                raise MethodNotAllowedError(self.request.method, status_code=403)
        else:
            result = self.patch_single(self.parse_pk(instance_id))

        self._call_postprocessor(result=result)
        self.finish(result)

    def patch_many(self) -> dict:
        """
            Patch many instances

            :statuscode 201: instances successfull modified

            :query limit: limit the count of modified instances
            :query single: If true sqlalchemy will raise an error if zero or more than one instances would be modified
        """

        # Flush
        self.model.session.flush()

        # Get values
        values = self.get_argument_values()

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_query_argument("limit", None)

        # Call Preprocessor
        self._call_preprocessor(filters=filters, data=values)

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
        return {'num_modified': num}

    def patch_single(self, instance_id: list) -> dict:
        """
            Patch one instance

            :param instance_id: query argument of request
            :type instance_id: list of primary keys

            :statuscode 201: instance successfull modified
            :statuscode 404: Error
        """
        try:
            with self.model.session.begin_nested():
                values = self.get_argument_values()

                # Call Preprocessor
                self._call_preprocessor(instance_id=instance_id, data=values)

                # Get Instance
                instance = self.model.get(*instance_id)

                # Set Values
                for (key, value) in values.items():
                    self.logger.debug("%r.%s => %s" % (instance, key, value))
                    setattr(instance, key, value)

                # Flush
                try:
                    self.model.session.flush()
                except SQLAlchemyError as ex:
                    logging.exception(ex)
                    self.model.session.rollback()
                    self.send_error(status_code=400, exc_info=sys.exc_info())
                    return

                # Refresh
                self.model.session.refresh(instance)

                # Set Status
                self.set_status(201, "Patched")

                # To Dict
                return self.to_dict(instance)
        except SQLAlchemyError as ex:
            logging.exception(ex)
            self.send_error(status_code=400, exc_info=sys.exc_info())
        finally:
            # Commit
            self.model.session.commit()

    def delete(self, instance_id: str=None):
        """
            DELETE (delete instance) request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 403: DELETE MANY disallowed
            :statuscode 405: DELETE disallowed
        """

        if not 'delete' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        self._call_preprocessor(search_params=self.search_params)

        if instance_id is None:
            if self.allow_patch_many:
                result = self.delete_many()
            else:
                raise MethodNotAllowedError(self.request.method, status_code=403)
        else:
            result = self.delete_single(self.parse_pk(instance_id))

        self._call_postprocessor(result=result)
        self.finish(result)

    def delete_many(self) -> dict:
        """
            Remove many instances

            :statuscode 200: instances successfull removed

            :query limit: limit the count of deleted instances
            :query single: If true sqlalchemy will raise an error if zero or more than one instances would be deleted
        """

        # Flush
        self.model.session.flush()

        # Filters
        filters = self.get_filters()

        # Limit
        limit = self.get_query_argument("limit", None)

        # Call Preprocessor
        self._call_preprocessor(filters=filters)

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
        return {'num_removed': num}

    def delete_single(self, instance_id: list) -> dict:
        """
            Get one instance

            :param instance_id: query argument of request
            :type instance_id: list of primary keys

            :statuscode 204: instance successfull removed
        """

        # Call Preprocessor
        self._call_preprocessor(instance_id=instance_id)

        # Get Instance
        instance = self.model.get(*instance_id)

        # Trigger deletion
        self.model.session.delete(instance)
        self.model.session.commit()

        # Status
        self.set_status(204, "Instance removed")
        return {}

    def put(self, instance_id: str=None):
        """
            PUT (update instance) request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 403: PUT MANY disallowed
            :statuscode 404: Error
            :statuscode 405: PUT disallowed
        """

        if not 'put' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        self._call_preprocessor(search_params=self.search_params)

        if instance_id is None:
            if self.allow_patch_many:
                result = self.put_many()
            else:
                raise MethodNotAllowedError(self.request.method, status_code=403)
        else:
            result = self.put_single(self.parse_pk(instance_id))

        self._call_postprocessor(result=result)
        self.finish(result)

    put_many = patch_many
    put_single = patch_single

    def post(self, instance_id: str=None):
        """
            POST (new input) request

            :param instance_id: (ignored)

            :statuscode 204: instance successfull created
            :statuscode 404: Error
            :statuscode 405: POST disallowed
        """

        if not 'post' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        self._call_preprocessor(search_params=self.search_params)

        result = self.post_single()

        self._call_postprocessor(result=result)
        self.finish(result)

    def post_single(self):
        """
            Post one instance
        """

        try:
            values = self.get_argument_values()

            # Call Preprocessor
            self._call_preprocessor(data=values)

            # Create Instance
            instance = self.model(**values)

            # Flush
            self.model.session.commit()

            # Refresh
            self.model.session.refresh(instance)

            # Set Status
            self.set_status(201, "Created")

            # To Dict
            return self.to_dict(instance)
        except SQLAlchemyError:
            self.send_error(status_code=400, exc_info=sys.exc_info())
            self.model.session.rollback()
        finally:
            # Commit
            self.model.session.commit()

    @memoized_instancemethod
    def get_content_encoding(self) -> str:
        """
        Get the encoding the client sends us for encoding request.body correctly

        :reqheader Content-Type: Provide a charset in addition for decoding arguments.
        """

        content_type_args = {k.strip(): v for k, v in parse_qs(self.request.headers['Content-Type']).items()}
        if 'charset' in content_type_args and content_type_args['charset']:
            return content_type_args['charset'][0]
        else:
            return 'latin1'

    @memoized_instancemethod
    def get_body_arguments(self) -> dict:
        """
            Get arguments encode as json body

            :statuscode 415: Content-Type mismatch

            :reqheader Content-Type: application/x-www-form-urlencoded or application/json
        """

        self.logger.debug(self.request.body)

        content_type = self.request.headers.get('Content-Type')
        if 'www-form-urlencoded' in content_type:
            payload = self.request.arguments
            for key, value in payload.items():
                if len(value) == 0:
                    payload[key] = None
                elif len(value) == 1:
                    payload[key] = str(value[0], encoding=self.get_content_encoding())
                else:
                    payload[key] = [str(value, encoding=self.get_content_encoding()) for value in value]
            return payload
        elif 'application/json' in content_type:
            return loads(str(self.request.body, encoding=self.get_content_encoding()))
        else:
            raise HTTPError(415, content_type=content_type)

    def get_body_argument(self, name: str, default=RequestHandler._ARG_DEFAULT):
        """
        Get an argument named key from json encoded body

        :param name: Name of argument
        :param default: Default value, if not provided HTTPError 404 is raised
        :return:

        :statuscode 404: Missing Argument
        """
        arguments = self.get_body_arguments()
        if name in arguments:
            return arguments[name]
        elif default is RequestHandler._ARG_DEFAULT:
            raise HTTPError(400, "Missing argument %s" % name)
        else:
            return default

    @property
    def search_params(self) -> dict:
        """
            The 'q' Dictionary
        """
        try:
            return self._search_params
        except AttributeError:
            self._search_params = loads(self.get_argument("q", default="{}"))
            return self._search_params

    def get_query_argument(self, name: str, default=RequestHandler._ARG_DEFAULT):
        """
        Get an argument named key from json encoded body

        :param name:
        :param default:
        :return:
        :raise: 400 Missing Argument

        :query q: The query argument
        """

        if name in self.search_params:
            return self.search_params[name]
        elif default is RequestHandler._ARG_DEFAULT:
            raise HTTPError(400, "Missing argument %s" % name)
        else:
            return default

    def get_argument(self, name: str, *args, **kwargs):
        """
            On PUT/PATCH many request parameter may be located in body instead of query

            :param name: Name of argument
            :param args: Additional position arguments @see tornado.web.RequestHandler.get_argument
            :param kwargs: Additional keyword arguments @see tornado.web.RequestHandler.get_argument
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

            :query q: (ignored)
        """

        # Include Columns
        if self.include is not None:
            values = {k: self.get_body_argument(k) for k in self.include}
        else:
            values = {k: v for k, v in self.get_body_arguments().items()}

        # Exclude "q"
        if "q" in values:
            del values["q"]

        # Exclude Columns
        if self.exclude is not None:
            for column in list(self.exclude):
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
        for relation_key, relation in self.model.relations.items():
            if relation_key in values:
                values_relations[relation_key] = values[relation_key]
                del values[relation_key]

        # Check Columns
        #for column in values:
        #    if not column in self.model.column_names:
        #        raise IllegalArgumentError("Column '%s' not defined for model %s" % (column, self.model.model))

        return values

    def get(self, instance_id: str=None):
        """
            GET request

            :param instance_id: query argument of request
            :type instance_id: comma seperated string list

            :statuscode 405: GET disallowed
        """

        if not 'get' in self.methods:
            raise MethodNotAllowedError(self.request.method)

        # Call Preprocessor
        self._call_preprocessor(search_params=self.search_params)

        if instance_id is None:
            result = self.get_many()
        else:
            result = self.get_single(self.parse_pk(instance_id))

        self._call_postprocessor(result=result)
        self.finish(result)

    def get_single(self, instance_id: list) -> dict:
        """
            Get one instance

            :param instance_id: query argument of request
            :type instance_id: list of primary keys
        """

        # Call Preprocessor
        self._call_preprocessor(instance_id=instance_id)

        # Get Instance
        instance = self.model.get(*instance_id)

        # To Dict
        return self.to_dict(instance)

    def get_many(self) -> dict:
        """
            Get all instances

            Note that it is possible to provide offset and page as argument then
            it will return instances of the nth page and skip offset items

            :statuscode 400: if results_per_page > max_results_per_page or offset < 0

            :query results_per_page: Overwrite the returned results_per_page
            :query offset: Skip offset instances
            :query page: Return nth page
            :query limit: limit the count of modified instances
            :query single: If true sqlalchemy will raise an error if zero or more than one instances would be deleted
        """

        # All search params
        search_params = {'single': self.get_query_argument("single", False),
                         'results_per_page': int(self.get_argument("results_per_page", self.results_per_page)),
                         'offset': int(self.get_query_argument("offset", 0))}

        # Results per Page Check
        if search_params['results_per_page'] > self.max_results_per_page:
            raise IllegalArgumentError("request.results_per_page > application.max_results_per_page")

        # Offset & Page
        page = int(self.get_argument("page", '1')) - 1
        search_params['offset'] += page * search_params['results_per_page']
        if search_params['offset'] < 0:
            raise IllegalArgumentError("request.offset < 0")

        # Limit
        search_params['limit'] = self.get_query_argument("limit", search_params['results_per_page'] or None)

        # Filters
        filters = self.get_filters()

        # Call Preprocessor
        self._call_preprocessor(filters=filters, search_params=search_params)

        # Num Results
        num_results = self.model.count(filters=filters)
        if search_params['results_per_page']:
            total_pages = ceil(num_results / search_params['results_per_page'])
        else:
            total_pages = 1

        # Get Instances
        if search_params['single']:
            instances = [self.model.one(offset=search_params['offset'], filters=filters)]
        else:
            instances = self.model.all(offset=search_params['offset'], limit=search_params['limit'], filters=filters)

        return {'num_results': num_results,
                "total_pages": total_pages,
                "page": page + 1,
                "objects": self.to_dict(instances)}

    def _call_preprocessor(self, *args, **kwargs):
        """
            Calls a preprocessor with args and kwargs
        """
        func_name = inspect.stack()[1][3]

        if func_name in self.preprocessor:
            for func in self.preprocessor[func_name]:
                func(*args, model=self.model, handler=self, **kwargs)

    def _call_postprocessor(self, *args, **kwargs):
        """
            Calls a postprocessor with args and kwargs
        """
        func_name = inspect.stack()[1][3]

        if func_name in self.postprocessor:
            for func in self.postprocessor[func_name]:
                func(*args, model=self.model, handler=self, **kwargs)

    @memoized_property
    def logger(self):
        """
            Tornado Restless Logger
        """
        return logging.getLogger('tornado.restless')

    def to_dict(self, instance):
        """
            Wrapper to convert.to_dict with arguments from blueprint init

            :param instance: Instance to be translated
        """
        return to_dict(instance,
                       include=self.include,
                       exclude=self.exclude,
                       options=self.to_dict_options)

    def parse_pk(self, instance_id):
        return instance_id.split(self.ID_SEPARATOR, self.pk_length - 1)
