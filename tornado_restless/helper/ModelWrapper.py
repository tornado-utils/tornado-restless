#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from collections import namedtuple
import inspect
from sqlalchemy import inspect as sqinspect
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.properties import RelationProperty
from sqlalchemy.sql.operators import is_ordering_modifier

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '27.04.13 - 00:14'


class ModelWrapper(object):
    """
        Wrapper around sqlalchemy model for having some easier functions
    """

    def __init__(self, model):
        self.model = model

    def primary_key_names(self):
        """
            Returns the names of all primary keys

            Inspired by flask-restless.helpers.primary_key_names
        """
        return [key for key, field in inspect.getmembers(self.model)
                if isinstance(field, QueryableAttribute)
                   and isinstance(field.property, ColumnProperty)
            and field.property.columns[0].primary_key]

    @staticmethod
    def get_primary_keys(instance):
        """
            Returns the primary keys

            Inspired by flask-restless.helpers.primary_key_names

            :param instance: Model ORM Instance
        """
        return [field for key, field in inspect.getmembers(instance)
                if isinstance(field, QueryableAttribute)
                   and isinstance(field.property, ColumnProperty)
            and field.property.columns[0].primary_key]

    @property
    def primary_keys(self):
        """
        @see get_primary_keys
        """
        return self.get_primary_keys(self.model)

    @staticmethod
    def get_columns(instance):
        """
            Returns the columns objects of the model

            :param instance: Model ORM Instance
        """
        if hasattr(instance, 'iterate_properties'):
            return [field for field in instance.iterate_properties
                    if isinstance(field, ColumnProperty)]
        else:
            return [field for key, field in inspect.getmembers(instance)
                    if isinstance(field, QueryableAttribute)
                and isinstance(field.property, ColumnProperty)]

    @property
    def columns(self):
        """
        @see get_columns
        """
        return self.get_columns(self.model)

    @property
    def column_names(self):
        return [p.key for p in self.get_columns(self.model)]

    @staticmethod
    def get_relations(instance):
        """
            Returns the relations objects of the model

            :param instance: Model ORM Instance
        """
        if hasattr(instance, 'iterate_properties'):
            return [field for field in instance.iterate_properties
                    if isinstance(field, RelationProperty)]
        else:
            return [field for key, field in inspect.getmembers(instance)
                    if isinstance(field, QueryableAttribute)
                and isinstance(field.property, RelationProperty)]

    @property
    def relations(self):
        """
        @see get_relations
        """
        return self.get_relations(self.model)

    @staticmethod
    def get_hybrids(instance):
        """
            Returns the relations objects of the model

            :param instance: Model ORM Instance
        """
        Proxy = namedtuple('Proxy', ['key', 'field'])
        if hasattr(instance, 'iterate_properties'):
            return [Proxy(key, field) for key, field in sqinspect(instance).all_orm_descriptors.items()
                    if isinstance(field, hybrid_property)]
        else:
            return [Proxy(key, field) for key, field in inspect.getmembers(instance)
                    if isinstance(field, hybrid_property)]

    @property
    def hybrids(self):
        """
        @see get_hybrids
        """
        return self.get_hybrids(self.model)

    @staticmethod
    def get_proxies(instance):
        """
            Returns the proxies objects of the model

            Inspired by https://groups.google.com/forum/?fromgroups=#!topic/sqlalchemy/aDi_M4iH7d0

            :param instance: Model ORM Instance
        """
        Proxy = namedtuple('Proxy', ['key', 'field'])
        if hasattr(instance, 'iterate_properties'):
            return [Proxy(key, field) for key, field in sqinspect(instance).all_orm_descriptors.items()
                    if isinstance(field, AssociationProxy)]
        else:
            return [Proxy(key, field) for key, field in inspect.getmembers(instance)
                    if isinstance(field, AssociationProxy)]

    @property
    def proxies(self):
        """
        @see get_proxies
        """
        return self.get_proxies(self.model)


class SessionedModelWrapper(ModelWrapper):
    """
        Wrapper around sqlalchemy model for having some easier functions
    """

    def __init__(self, model, session):
        super().__init__(model)
        self.session = session

    def one(self, offset: int=None, filters: list=()) -> object:
        """
            Gets one instance of the model filtered by filters

            :param offset: Offset for request
            :param filters: Filters and OrderBy Clauses
        """
        instance = self.session.query(self.model)
        for expression in filters:
            if is_ordering_modifier(expression.operator):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter_by(expression)
        if offset is not None:
            instance = instance.offset(offset)
        return instance.one()

    def all(self, offset: int=None, limit: int=None, filters: list=()) -> list:
        """
            Gets all instances of the model filtered by filters

            :param offset: Offset for request
            :param limit: Limit for request
            :param filters: Filters and OrderBy Clauses
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

    def update(self, values: dict, offset: int=None, limit: int=None, filters: list=()) -> int:
        """
            Updates all instances of the model filtered by filters

            :param values: Dictionary of values
            :param offset: Offset for request
            :param limit: Limit for request
            :param filters: Filters and OrderBy Clauses
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
        return instance.update(values)

    def count(self, filters: list=()) -> int:
        """
            Gets the instance count

            :param filters: Filters and OrderBy Clauses
        """
        instance = self.session.query(self.model)
        for expression in filters:
            instance = instance.filter_by(expression)
        return instance.count()

    def get(self, primary_keys) -> object:
        """
            Gets one instance of the model based on primary_keys

            :param primary_keys: values of primary_keys
        """
        if len(primary_keys) == 1:
            primary_keys = primary_keys[0]
        else:
            primary_keys = tuple(primary_keys)
        instance = self.session.query(self.model).get(primary_keys)
        if not instance:
            raise NoResultFound("No row was found for get()")
        return instance

    def __call__(self, **kwargs):
        instance = self.model()
        for key, value in kwargs:
            setattr(instance, key, value)
        self.session.add(instance)
        return instance





