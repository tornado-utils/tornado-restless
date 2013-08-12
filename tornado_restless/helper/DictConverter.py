#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from datetime import datetime, date, time
from sqlalchemy.orm import object_mapper
from sqlalchemy.orm.exc import UnmappedInstanceError
from tornado_restless.helper.IllegalArgumentError import IllegalArgumentError
from tornado_restless.helper.ModelWrapper import ModelWrapper

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '23.05.13 - 17:41'


def to_filter(instance,
              filters=None,
              order_by=None):
    """
        Returns a list of filters made by arguments

        :param instance:
        :param filters: List of filters in restless 3-tuple op string format
        :param order_by: List of orders to be appended aswell
    """

    # Get all provided filters
    argument_filters = filters and filters or []

    # Parse order by as filters
    argument_orders = order_by and order_by or []
    for argument_order in argument_orders:
        direction = argument_order['direction']
        if direction not in ["asc", "desc"]:
            raise IllegalArgumentError("Direction unkown")
        argument_filters.append({'name': argument_order['field'], 'op': direction})

    # Create Alchemy Filters
    alchemy_filters = []
    for argument_filter in argument_filters:

        left = getattr(instance, argument_filter["name"])
        op = argument_filter["op"]

        if "field" in argument_filter.keys():
            right = getattr(instance, argument_filter["field"])
        elif "val" in argument_filter.keys():
            right = argument_filter["val"]
        elif "value" in argument_filter.keys():  # Because we hate abbr sometimes ...
            right = argument_filter["value"]
        else:
            right = None

        # Operators from flask-restless
        if op in ["is_null"]:
            alchemy_filters.append(left.is_(None))
        elif op in ["is_not_null"]:
            alchemy_filters.append(left.isnot(None))
        elif op in ["is"]:
            alchemy_filters.append(left.is_(right))
        elif op in ["is_not"]:
            alchemy_filters.append(left.isnot(right))
        elif op in ["==", "eq", "equals", "equals_to"]:
            alchemy_filters.append(left == right)
        elif op in ["!=", "ne", "neq", "not_equal_to", "does_not_equal"]:
            alchemy_filters.append(left != right)
        elif op in [">", "gt"]:
            alchemy_filters.append(left > right)
        elif op in ["<", "lt"]:
            alchemy_filters.append(left < right)
        elif op in [">=", "ge", "gte", "geq"]:
            alchemy_filters.append(left >= right)
        elif op in ["<=", "le", "lte", "leq"]:
            alchemy_filters.append(left <= right)
        elif op in ["ilike"]:
            alchemy_filters.append(left.ilike(right))
        elif op in ["not_ilike"]:
            alchemy_filters.append(left.notilike(right))
        elif op in ["like"]:
            alchemy_filters.append(left.like(right))
        elif op in ["not_like"]:
            alchemy_filters.append(left.notlike(right))
        elif op in ["match"]:
            alchemy_filters.append(left.match(right))
        elif op in ["in"]:
            alchemy_filters.append(left.in_(right))
        elif op in ["not_in"]:
            alchemy_filters.append(left.notin_(right))
        elif op in ["has"]:
            alchemy_filters.append(left.has(right))
        elif op in ["any"]:
            alchemy_filters.append(left.any(right))

        # Additional Operators
        elif op in ["between"]:
            alchemy_filters.append(left.between(*right))
        elif op in ["contains"]:
            alchemy_filters.append(left.contains(right))
        elif op in ["startswith"]:
            alchemy_filters.append(left.startswith(right))
        elif op in ["endswith"]:
            alchemy_filters.append(left.endswith(right))

        # Order By Operators
        elif op in ["asc"]:
            alchemy_filters.append(left.asc())
        elif op in ["desc"]:
            alchemy_filters.append(left.asc())

        # Raise Exception
        else:
            raise IllegalArgumentError("Unknown operator")
    return alchemy_filters


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

    # Date / Time
    if isinstance(instance, datetime) or isinstance(instance, time) or isinstance(instance, date):
        return instance.isoformat()

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