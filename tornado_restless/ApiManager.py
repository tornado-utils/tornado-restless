#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
import sqlalchemy.orm
from sqlalchemy.util import memoized_property
from tornado.web import Application, URLSpec

from .handler.BaseHandler import BaseHandler
from .helper.IllegalArgumentError import IllegalArgumentError

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '26.04.13 - 22:25'


class ApiManager(object):
    METHODS_READ = frozenset(['GET'])
    METHODS_MODIFY = frozenset(['POST', 'PUT', 'PATCH'])
    METHODS_DELETE = frozenset(['DELETE'])

    METHODS_UPDATE = METHODS_READ | METHODS_MODIFY
    METHODS_ALL = METHODS_READ | METHODS_MODIFY | METHODS_DELETE

    def __init__(self,
                 application: Application,
                 session: sqlalchemy.orm.Session=None,
                 Session: type=None):
        """

        :param Session: is a sqlalchemy.orm.Session class
        :param session: is a sqlalchemy.orm.Session object
        :param application: is the tornado.web.Application object
        """
        self.application = application

        if Session is None and session is None:
            raise IllegalArgumentError("Either session or Session must be defined")

        self.Session = Session
        if session is not None:
            self._session = session

    @memoized_property
    def session(self):
        """
            Create a session object from Session() or use an existing session
        """
        if hasattr(self, '_session'):
            return self._session
        return self.Session()

    def create_api_blueprint(self,
                             model,
                             methods: set=METHODS_READ,
                             url_prefix: str='/api',
                             collection_name: str=None,
                             allow_patch_many: bool=False,
                             allow_method_override: bool=False,
                             validation_exceptions=None,
                             include_columns=None,
                             exclude_columns=None,
                             results_per_page: int=10,
                             max_results_per_page: int=100,
                             blueprint_prefix: str='',
                             handler_class: BaseHandler=BaseHandler) -> URLSpec:
        """


        :param model:
        :param methods: Allow methods
        :param url_prefix: The url prefix of the application
        :param collection_name:
        :param allow_patch_many: Allow PATCH with multiple datasets
        :param allow_method_override: Support X-HTTP-Method-Override Header
        :param validation_exceptions:
        :param include_columns:
        :param exclude_columns:
        :param results_per_page: The default value of how many results are returned per request
        :param max_results_per_page: The hard upper limit of resutest per page
        :param blueprint_prefix: The Prefix that will be used to unique collection_name for named_handlers
        :param handler_class: The Handler Class that will be registered, for customisation extend BaseHandler
        :return: :class:`tornado.web.URLSpec`
        :raise: IllegalArgumentError
        """
        if exclude_columns is not None and include_columns is not None:
            raise IllegalArgumentError('Cannot simultaneously specify both include columns and exclude columns.')

        table_name = collection_name if collection_name is not None else model.__tablename__

        kwargs = {'model': model,
                  'manager': self,
                  'methods': methods,
                  'allow_patch_many': allow_patch_many,
                  'allow_method_override': allow_method_override,
                  'validation_exceptions': validation_exceptions,
                  'include_columns': include_columns,
                  'exclude_columns': exclude_columns,
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
        Creates and registers a route for the model

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