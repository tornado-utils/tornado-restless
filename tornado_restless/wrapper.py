#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from collections import namedtuple
import inspect
import logging
from sqlalchemy import inspect as sqinspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty, Query
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.interfaces import MapperProperty
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.sql.operators import is_ordering_modifier
from sqlalchemy.util import memoized_property

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '27.04.13 - 00:14'


def _filter(instance, condition) -> dict:
    """
        Filter properties of instace based on condition

        :param instance:
        :param condition:
        :rtype: dict
    """

    # Use iterate_properties when available
    if hasattr(instance, 'iterate_properties'):
        return {field.key: field for field in instance.iterate_properties
                if condition(field)}

    # Try sqlalchemy inspection
    try:
        return {field.key: field for key, field in sqinspect(instance).all_orm_descriptors.items()
                if condition(field)}

    # Use Inspect
    except NoInspectionAvailable:
        return {field.key: field for key, field in inspect.getmembers(instance)
                if condition(field)}


def _is_ordering_expression(expression):
    """
        Test an expression whether it is an ordering clause
    """

    if hasattr(expression, 'operator') and is_ordering_modifier(expression.operator):
        return True

    if hasattr(expression, 'modifier') and is_ordering_modifier(expression.modifier):
        return True

    return False


class ModelWrapper(object):
    """
        Wrapper around sqlalchemy model for having some easier functions
    """

    def __init__(self, model):
        self.model = model

    @property
    def __name__(self):
        return self.model.__name__

    @property
    def __tablename__(self):
        return self.model.__tablename__

    @property
    def __collectionname__(self):
        try:
            return self.model.__collectionname__
        except AttributeError:
            logging.warning("Missing collection name for %s using tablename" % self.model.__name__)
            return self.model.__tablename__

    @staticmethod
    def get_primary_keys(instance) -> dict:
        """
            Returns the primary keys

            Inspired by flask-restless.helpers.primary_key_names

            :param instance: Model ORM Instance
        """
        return _filter(instance, lambda field: isinstance(field, ColumnProperty) and field.primary_key or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, ColumnProperty) and field.property.columns[0].primary_key))

    @memoized_property
    def primary_keys(self):
        """
        @see get_primary_keys
        """
        return self.get_primary_keys(self.model)

    @staticmethod
    def get_unique_keys(instance) -> dict:
        """
            Returns the primary keys

            Inspired by flask-restless.helpers.primary_key_names

            :param instance: Model ORM Instance
        """
        return _filter(instance, lambda field: isinstance(field, ColumnProperty) and field.unique or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, ColumnProperty) and field.property.columns[0].unique))

    @memoized_property
    def unique_keys(self):
        """
        @see get_primary_keys
        """
        return self.get_unique_keys(self.model)

    @staticmethod
    def get_foreign_keys(instance) -> list:
        """
            Returns the foreign keys

            Inspired by flask-restless.helpers.primary_key_names

            :param instance: Model ORM Instance
        """
        return {field.key: field for key, field in inspect.getmembers(instance)
                if isinstance(field, QueryableAttribute)
                   and isinstance(field.property, ColumnProperty)
        and field.foreign_keys}

    @memoized_property
    def foreign_keys(self):
        """
        @see get_foreign_keys
        """
        return self.get_foreign_keys(self.model)

    @staticmethod
    def get_columns(instance) -> dict:
        """
            Returns the columns objects of the model

            :param instance: Model ORM Instance
        """
        return _filter(instance, lambda field: isinstance(field, ColumnProperty) or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, ColumnProperty)))

    @memoized_property
    def columns(self):
        """
        @see get_columns
        """
        return self.get_columns(self.model)

    @staticmethod
    def get_attributes(instance) -> dict:
        """
            Returns the attributes of the model

            :param instance: Model ORM Instance
        """
        return _filter(instance,
                       lambda field: isinstance(field, MapperProperty) or isinstance(field, QueryableAttribute))

    @memoized_property
    def attributes(self):
        """
        @see get_attributes
        """
        return self.get_attributes(self.model)

    @staticmethod
    def get_relations(instance) -> dict:
        """
            Returns the relations objects of the model

            :param instance: Model ORM Instance
        """
        return _filter(instance, lambda field: isinstance(field, RelationshipProperty) or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, RelationshipProperty)))

    @memoized_property
    def relations(self):
        """
        @see get_relations
        """
        return self.get_relations(self.model)

    @staticmethod
    def get_hybrids(instance) -> list:
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

    @memoized_property
    def hybrids(self) -> list:
        """
        @see get_hybrids
        """
        return self.get_hybrids(self.model)

    @staticmethod
    def get_proxies(instance) -> list:
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

    @memoized_property
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
            if _is_ordering_expression(expression):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter_by(expression)
        if offset is not None:
            instance = instance.offset(offset)
        return instance.one()

    @staticmethod
    def get_all(instance: Query, offset: int=None, limit: int=None, filters: list=()) -> list:
        """
            Gets all instances of the query instance

            :param instance: sqlalchemy queriable
            :param offset: Offset for request
            :param limit: Limit for request
            :param filters: Filters and OrderBy Clauses
        """
        for expression in filters:
            if _is_ordering_expression(expression):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter(expression)
        if offset is not None:
            instance = instance.offset(offset)
        if limit is not None:
            instance = instance.limit(limit)
        return instance.all()

    def all(self, offset: int=None, limit: int=None, filters: list=()) -> list:
        """
            Gets all instances of the model filtered by filters

            :param offset: Offset for request
            :param limit: Limit for request
            :param filters: Filters and OrderBy Clauses
        """
        instance = self.session.query(self.model)
        return self.get_all(instance, offset=offset, limit=limit, filters=filters)

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
            if _is_ordering_expression(expression):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter_by(expression)
        if offset is not None:
            instance = instance.offset(offset)
        if limit is not None:
            instance = instance.limit(limit)
        return instance.update(values)

    def delete(self, offset: int=None, limit: int=None, filters: list=()) -> int:
        """
            Delete all instances of the model filtered by filters

            :param offset: Offset for request
            :param limit: Limit for request
            :param filters: Filters and OrderBy Clauses
        """
        instance = self.session.query(self.model)
        for expression in filters:
            if _is_ordering_expression(expression):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter_by(expression)
        if offset is not None:
            instance = instance.offset(offset)
        if limit is not None:
            instance = instance.limit(limit)
        return instance.delete()

    def count(self, filters: list=()) -> int:
        """
            Gets the instance count

            :param filters: Filters and OrderBy Clauses
        """
        instance = self.session.query(self.model)
        for expression in filters:
            if _is_ordering_expression(expression):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter(expression)
        return instance.count()

    def get(self, instance_id: list) -> object:
        """
            Gets one instance of the model based on primary_keys

            :param instance_id: list of primary_keys
        """
        if len(instance_id) == 1:
            primary_keys = instance_id[0]
        else:
            primary_keys = tuple(instance_id)
        instance = self.session.query(self.model).get(primary_keys)
        if not instance:
            raise NoResultFound("No row was found for get()")
        return instance

    def __call__(self, **kwargs):
        instance = self.model()
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.add(instance)
        return instance





