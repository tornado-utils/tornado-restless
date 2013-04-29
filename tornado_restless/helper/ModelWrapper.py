#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
import inspect
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.operators import is_ordering_modifier

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '27.04.13 - 00:14'


class ModelWrapper(object):
    """
        Wrapper around sqlalchemy model for having some easier functions
    """

    def __init__(self, model, session):
        self.model = model
        self.session = session

    def primary_key_names(self):
        """
            Returns the names of all primary keys

            Inspired by flask-restless.helpers.primary_key_names
        """
        return [key for key, field in inspect.getmembers(self.model)
                if isinstance(field, QueryableAttribute)
                   and isinstance(field.property, ColumnProperty)
            and field.property.columns[0].primary_key]

    def primary_keys(self):
        """
            Returns the primary keys

            Inspired by flask-restless.helpers.primary_key_names
        """
        return [field for key, field in inspect.getmembers(self.model)
                if isinstance(field, QueryableAttribute)
                   and isinstance(field.property, ColumnProperty)
            and field.property.columns[0].primary_key]

    def one(self, filters):
        """
            Gets one instance of the model filtered by filters
        """
        instance = self.session.query(self.model)
        for expression in filters:
            instance = instance.filter_by(expression)
        return instance.one()

    def all(self, offset=None, limit=None, filters=()):
        """
            Gets all instances of the model filtered by filters
        """
        instance = self.session.query(self.model)
        for expression in filters:
            if is_ordering_modifier(expression.operator):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter_by(expression)
        if offset is not None:
            instance = instance.offset(offset)
        if limit is not None:
            instance = instance.limit(limit)
        return instance.all()

    def count(self, filters=()):
        """
            Gets the instance count
        """

        instance = self.session.query(self.model)
        for expression in filters:
            instance = instance.filter_by(expression)
        return instance.count()

    def get(self, primary_keys):
        """
            Gets one instance of the model based on primary_keys
            :param primary_keys: values of primary_keys
        """

        # Transform to tuple
        if len(primary_keys) == 1:
            primary_keys = primary_keys[0]
        else:
            primary_keys = tuple(primary_keys)

        instance = self.session.query(self.model).get(primary_keys)
        if not instance:
            raise NoResultFound("No row was found for get()")
        return instance





