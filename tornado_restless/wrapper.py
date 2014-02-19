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
        """
        return _filter(instance, lambda field: isinstance(field, ColumnProperty) and field.primary_key or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, ColumnProperty) and field.property.columns[0].primary_key))

    @memoized_property
    def primary_keys(self):
        """
        @see get_primary_keys
        """
        return self.get_primary_keys(self.model)

    primary_keys.__doc__ = get_primary_keys.__func__.__doc__

    @staticmethod
    def get_unique_keys(instance) -> dict:
        """
            Returns the primary keys

            Inspired by flask-restless.helpers.primary_key_names
        """
        return _filter(instance, lambda field: isinstance(field, ColumnProperty) and field.unique or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, ColumnProperty) and field.property.columns[0].unique))

    @memoized_property
    def unique_keys(self):
        """
        @see get_primary_keys
        """
        return self.get_unique_keys(self.model)

    unique_keys.__doc__ = get_unique_keys.__func__.__doc__

    @staticmethod
    def get_foreign_keys(instance) -> list:
        """
            Returns the foreign keys

            Inspired by flask-restless.helpers.primary_key_names
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

    foreign_keys.__doc__ = get_foreign_keys.__func__.__doc__

    @staticmethod
    def get_columns(instance) -> dict:
        """
            Returns the columns objects of the model
        """
        return _filter(instance, lambda field: isinstance(field, ColumnProperty) or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, ColumnProperty)))

    @memoized_property
    def columns(self):
        """
        @see get_columns
        """
        return self.get_columns(self.model)

    columns.__doc__ = get_columns.__func__.__doc__

    @staticmethod
    def get_attributes(instance) -> dict:
        """
            Returns the attributes of the model
        """
        return _filter(instance,
                       lambda field: isinstance(field, MapperProperty) or isinstance(field, QueryableAttribute))

    @memoized_property
    def attributes(self):
        """
        @see get_attributes
        """
        return self.get_attributes(self.model)

    attributes.__doc__ = get_attributes.__func__.__doc__

    @staticmethod
    def get_relations(instance) -> dict:
        """
            Returns the relations objects of the model
        """
        return _filter(instance, lambda field: isinstance(field, RelationshipProperty) or (
            isinstance(field, QueryableAttribute) and isinstance(field.property, RelationshipProperty)))

    @memoized_property
    def relations(self):
        """
        @see get_relations
        """
        return self.get_relations(self.model)

    relations.__doc__ = get_relations.__func__.__doc__

    @staticmethod
    def get_hybrids(instance) -> list:
        """
            Returns the relations objects of the model
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

    hybrids.__doc__ = get_hybrids.__func__.__doc__

    @staticmethod
    def get_proxies(instance) -> list:
        """
            Returns the proxies objects of the model

            Inspired by https://groups.google.com/forum/?fromgroups=#!topic/sqlalchemy/aDi_M4iH7d0
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

    proxies.__doc__ = get_proxies.__func__.__doc__


class SessionedModelWrapper(ModelWrapper):
    """
        Wrapper around sqlalchemy model for having some easier functions
    """

    def __init__(self, model, session):
        super().__init__(model)
        self.session = session

    @staticmethod
    def _apply_kwargs(instance: Query, **kwargs) -> Query:
        for expression in kwargs.pop('filters', []):
            if _is_ordering_expression(expression):
                instance = instance.order_by(expression)
            else:
                instance = instance.filter(expression)

        if 'offset' in kwargs:
            offset = kwargs.pop('offset')
            foffset = lambda instance: instance.offset(offset)
        else:
            foffset = lambda instance: instance

        if 'limit' in kwargs:
            limit = kwargs.pop('limit')
            flimit = lambda instance: instance.limit(limit)
        else:
            flimit = lambda instance: instance

        instance = instance.filter_by(**kwargs)
        instance = foffset(instance)
        instance = flimit(instance)
        return instance

    def one(self, filters: list=(), **kwargs) -> object:
        """
            Gets one instance of the model filtered by filters

            :param filters: Filters and OrderBy Clauses
            :param kwargs: Additional filters passed to filter_by
            :keyword offset: Offset for request
        """
        if isinstance(self, SessionedModelWrapper):
            instance = self.session.query(self.model)
        else:
            instance = self

        return SessionedModelWrapper._apply_kwargs(instance, filters=filters, **kwargs).one()

    def all(self, filters: list=(), **kwargs) -> list:
        """
            Gets all instances of the query instance

            :param filters: Filters and OrderBy Clauses
            :param kwargs: Additional filters passed to filter_by
            :keyword limit: Limit for request
            :keyword offset: Offset for request
        """
        if isinstance(self, SessionedModelWrapper):
            instance = self.session.query(self.model)
        else:
            instance = self

        return SessionedModelWrapper._apply_kwargs(instance, filters=filters, **kwargs).all()

    def update(self, values: dict, filters: list=(), **kwargs) -> int:
        """
            Updates all instances of the model filtered by filters

            :param values: Dictionary of values
            :param filters: Filters and OrderBy Clauses
            :param kwargs: Additional filters passed to filter_by
            :keyword limit: Limit for request
            :keyword offset: Offset for request
        """
        if isinstance(self, SessionedModelWrapper):
            instance = self.session.query(self.model)
        else:
            instance = self

        return SessionedModelWrapper._apply_kwargs(instance, filters=filters, **kwargs).update(values)

    def delete(self, filters: list=(), **kwargs) -> int:
        """
            Delete all instances of the model filtered by filters

            :param values: Dictionary of values
            :param filters: Filters and OrderBy Clauses
            :param kwargs: Additional filters passed to filter_by
            :keyword limit: Limit for request
            :keyword offset: Offset for request
        """
        if isinstance(self, SessionedModelWrapper):
            instance = self.session.query(self.model)
        else:
            instance = self

        return SessionedModelWrapper._apply_kwargs(instance, filters=filters, **kwargs).delete()

    def count(self, filters: list=(), **kwargs) -> int:
        """
            Gets the instance count

            :param filters: Filters and OrderBy Clauses
            :param kwargs: Additional filters passed to filter_by
        """
        if isinstance(self, SessionedModelWrapper):
            instance = self.session.query(self.model)
        else:
            instance = self

        return SessionedModelWrapper._apply_kwargs(instance, filters=filters, **kwargs).count()

    def get(self, *pargs) -> object:
        """
            Gets one instance of the model based on primary_keys

            :param pargs: ident
            :raise NoResultFound: If no element has been received
        """
        if isinstance(self, SessionedModelWrapper):
            instance = self.session.query(self.model)
        else:
            instance = self

        if not isinstance(pargs, tuple):
            rtn = instance.get(*pargs)
        else:
            rtn = instance.get(pargs)

        if not rtn:
            raise NoResultFound("No element recieved for %s(%s)" % (self.model.__collectionname__, pargs))

        return rtn

    def __call__(self, **kwargs):
        instance = self.model()
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.add(instance)
        return instance





