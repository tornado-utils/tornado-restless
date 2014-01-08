#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from tornado.web import Application, URLSpec

from .handler import BaseHandler
from .errors import IllegalArgumentError

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '26.04.13 - 22:25'


class ApiManager(object):
    """
        The tornado restless engine

        You normally only need one instance of this class to spawn your tornado routes
    """

    METHODS_READ = frozenset(['GET'])
    METHODS_MODIFY = frozenset(['POST', 'PUT', 'PATCH'])
    METHODS_DELETE = frozenset(['DELETE'])

    METHODS_UPDATE = METHODS_READ | METHODS_MODIFY
    METHODS_ALL = METHODS_READ | METHODS_MODIFY | METHODS_DELETE

    def __init__(self,
                 application: Application,
                 session_maker: type=None):
        """
        Create an instance of the tornado restless engine

        :param session_maker: is a sqlalchemy.orm.Session class factory
        :param application: is the tornado.web.Application object
        """
        self.application = application

        self.session_maker = session_maker

    def create_api_blueprint(self,
                             model,
                             methods: set=METHODS_READ,
                             preprocessor: dict=None,
                             postprocessor: dict=None,
                             url_prefix: str='/api',
                             collection_name: str=None,
                             allow_patch_many: bool=False,
                             allow_method_override: bool=False,
                             validation_exceptions=None,
                             exclude_queries: bool=False,
                             exclude_hybrids: bool=False,
                             include_columns: list=None,
                             exclude_columns: list=None,
                             results_per_page: int=10,
                             max_results_per_page: int=100,
                             blueprint_prefix: str='',
                             handler_class: type=BaseHandler) -> URLSpec:
        """
        Create a tornado route for a sqlalchemy model

        :param model: The sqlalchemy model
        :param methods: Allowed methods for this model
        :param url_prefix: The url prefix of the application
        :param collection_name:
        :param allow_patch_many: Allow PATCH with multiple datasets
        :param allow_method_override: Support X-HTTP-Method-Override Header
        :param validation_exceptions:
        :param exclude_queries: Don't execude dynamic queries (like from associations or lazy relations)
        :param exclude_hybrids: When exclude_queries is True and exclude_hybrids is False, hybrids are still included.
        :param include_columns: Whitelist of columns to be included
        :param exclude_columns: Blacklist of columns to be excluded
        :param results_per_page: The default value of how many results are returned per request
        :param max_results_per_page: The hard upper limit of resutest per page
        :param blueprint_prefix: The Prefix that will be used to unique collection_name for named_handlers
        :param preprocessor: A dictionary of list of preprocessors that get called
        :param postprocessor: A dictionary of list of postprocessor that get called
        :param handler_class: The Handler Class that will be used in the route
        :type handler_class: tornado_restless.handler.BaseHandler or a subclass
        :return: :class:`tornado.web.URLSpec`
        :raise: IllegalArgumentError
        """
        if exclude_columns is not None and include_columns is not None:
            raise IllegalArgumentError('Cannot simultaneously specify both include columns and exclude columns.')

        table_name = collection_name if collection_name is not None else model.__tablename__

        kwargs = {'model': model,
                  'manager': self,
                  'methods': methods,
                  'preprocessor': preprocessor or {},
                  'postprocessor': postprocessor or {},
                  'allow_patch_many': allow_patch_many,
                  'allow_method_override': allow_method_override,
                  'validation_exceptions': validation_exceptions,
                  'include_columns': include_columns,
                  'exclude_columns': exclude_columns,
                  'exclude_queries': exclude_queries,
                  'exclude_hybrids': exclude_hybrids,
                  'results_per_page': results_per_page,
                  'max_results_per_page': max_results_per_page}

        blueprint = URLSpec(
            "%s/%s(?:/(.+))?[/]?" % (url_prefix, table_name),
            handler_class,
            kwargs,
            '%s%s' % (blueprint_prefix, table_name))
        return blueprint

    def create_api(self,
                   model,
                   virtualhost=r".*$", *args, **kwargs):
        """
        Creates and registers a route for the model in your tornado application

        The positional and keyword arguments are passed directly to the create_api_blueprint method

        :param model:
        :param virtualhost: bindhost for binding, .*$ in default
        """
        blueprint = self.create_api_blueprint(model, *args, **kwargs)

        for vhost, handlers in self.application.handlers:
            if vhost == virtualhost:
                handlers.append(blueprint)
                break
        else:
            self.application.add_handlers(virtualhost, [blueprint])

        self.application.named_handlers[blueprint.name] = blueprint