#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from sqlalchemy.orm import Session
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
                 session: Session):
        """

        :param session: is the sqlalchemy.orm.Session object
        :param application: is the tornado.web.Application object
        """
        self.application = application
        self.session = session

    def create_api_blueprint(self,
                             model,
                             methods=METHODS_READ,
                             url_prefix='/api',
                             collection_name=None,
                             allow_patch_many: bool=False,
                             allow_method_override: bool=False,
                             validation_exceptions=None,
                             include_columns=None,
                             exclude_columns=None,
                             results_per_page: int=10,
                             max_results_per_page: int=100,
                             blueprint_prefix='',
                             handler_class: BaseHandler=BaseHandler) -> URLSpec:
        """


        :param model:
        :param methods:
        :param url_prefix:
        :param collection_name:
        :param allow_patch_many: Allow PATCH with multiple datasets
        :param allow_method_override: Support X-HTTP-Method-Override Header
        :param validation_exceptions:
        :param include_columns:
        :param exclude_columns:
        :param results_per_page:
        :param max_results_per_page:
        :param blueprint_prefix: The Prefix that will be used to unique collection_name for named_handlers
        :param handler_class: The Handler Class that will be registered, for customisation extend BaseHandler
        :return: tornado route
        :raise: IllegalArgumentError
        """
        if exclude_columns is not None and include_columns is not None:
            raise IllegalArgumentError('Cannot simultaneously specify both include columns and exclude columns.')

        table_name = collection_name if collection_name is not None else model.__tablename__

        kwargs = {'model': model,
                  'session': self.session,
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