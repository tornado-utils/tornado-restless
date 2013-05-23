#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from sqlalchemy.orm import object_mapper
from sqlalchemy.orm.exc import UnmappedInstanceError
from tornado_restless.helper.ModelWrapper import ModelWrapper

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '23.05.13 - 17:41'


def to_dict(instance,
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

    # None
    if instance is None:
        return None

    # Plain List [Continue deepness]
    if isinstance(instance, list):
        return [to_dict(x, include_relations=include_relations) for x in instance]

    # Plain Dictionary [Continue deepness]
    if isinstance(instance, dict):
        return {k: to_dict(v, include_relations=include_relations) for k, v in instance.items()}

    # Int
    if isinstance(instance, int):
        return instance

    # String
    if isinstance(instance, str):
        return instance

    # Any Dictionary Object (e.g. _AssociationDict) [Stop deepness]
    if isinstance(instance, dict) or hasattr(instance, 'items'):
        return {k: to_dict(v, include_relations=()) for k, v in instance.items()}

    # Any Iterable Object (e.g. _AssociationList) [Stop deepness]
    if isinstance(instance, list) or hasattr(instance, '__iter__'):
        return [to_dict(x, include_relations=()) for x in instance]

    # Include Columns given
    if include_columns is not None:
        rtn = {}
        for column in include_columns:
            rtn[column] = to_dict(getattr(instance, column))
        for (column, include_relation) in include_relations.items():
            rtn[column] = to_dict(getattr(instance, column),
                                  include_columns=include_relations[0],
                                  include_relations=include_relations[1])
        return rtn

    if exclude_columns is None:
        exclude_columns = []

    if exclude_relations is None:
        exclude_relations = {}

    # SQLAlchemy instance?
    try:
        get_columns = [p.key for p in ModelWrapper.get_columns(object_mapper(instance))]
        get_relations = [p.key for p in ModelWrapper.get_relations(object_mapper(instance))]
        get_proxies = [p.key for p in ModelWrapper.get_proxies(object_mapper(instance))]
        get_hybrids = [p.key for p in ModelWrapper.get_hybrids(object_mapper(instance))]

        rtn = {}

        # Include Columns
        for column in get_columns:
            if not column in exclude_columns:
                rtn[column] = to_dict(getattr(instance, column))

        # Include AssociationProxy (may be list/dict/col so check for exclude_relations and exclude_columns)
        for column in get_proxies:
            if exclude_relations is not None and column in exclude_relations:
                continue
            if exclude_columns is not None and column in exclude_columns:
                continue
            if include_relations is None or column in include_relations:
                try:
                    rtn[column] = to_dict(getattr(instance, column))
                except AttributeError:
                    rtn[column] = None

        # Include Hybrid Properties
        for column in get_hybrids:
            if not column in exclude_columns:
                rtn[column] = to_dict(getattr(instance, column))

        # Include Relations but only one deep
        for column in get_relations:
            if exclude_relations is not None and column in exclude_relations:
                continue
            if include_relations is None or column in include_relations:
                rtn[column] = to_dict(getattr(instance, column), include_relations=())

        return rtn
    except UnmappedInstanceError as ex:
        raise ex