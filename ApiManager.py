#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from sqlalchemy.orm import Session
from tornado.web import Application, URLSpec
from api.handler.BaseHandler import BaseHandler
from api.helper.IllegalArgumentError import IllegalArgumentError

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '26.04.13 - 22:25'


class ApiManager(object):
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
                             methods=frozenset(['GET']),
                             url_prefix='/api',
                             collection_name=None,
                             allow_patch_many: bool=False,
                             validation_exceptions=None,
                             include_columns=None,
                             exclude_columns=None,
                             results_per_page: int=10,
                             max_results_per_page: int=100) -> URLSpec:
        """

        :param model:
        :param methods:
        :param url_prefix:
        :param collection_name:
        :param allow_patch_many:
        :param validation_exceptions:
        :param include_columns:
        :param exclude_columns:
        :param results_per_page:
        :param max_results_per_page:
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
                  'validation_exceptions': validation_exceptions,
                  'include_columns': include_columns,
                  'exclude_columns': exclude_columns,
                  'results_per_page': results_per_page,
                  'max_results_per_page': max_results_per_page}

        blueprint = URLSpec("%s/%s(/\d+)?" % (url_prefix, table_name), BaseHandler, kwargs, table_name)
        return blueprint

    def create_api(self, model, *args, **kwargs):
        """
        Creates and registers a route for the model

        The positional and keyword arguments are passed directly to the
        :meth:`create_api_blueprint` method, so see the documentation there.
        """
        blueprint = self.create_api_blueprint(model, *args, **kwargs)
        self.application.handlers[-1] = (
            self.application.handlers[-1][0], self.application.handlers[-1][1] + [blueprint])
        self.application.named_handlers[blueprint.name] = blueprint