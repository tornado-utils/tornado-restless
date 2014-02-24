#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
from datetime import datetime, date, time
import collections
import itertools

from sqlalchemy.orm import object_mapper
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.orm.query import Query

from .errors import IllegalArgumentError, DictConvertionError
from .wrapper import ModelWrapper


__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '23.05.13 - 17:41'

__datetypes__ = (datetime, time, date)
__basetypes__ = (str, int, bool, float)


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
            raise IllegalArgumentError("Direction unknown")
        argument_filters.append({'name': argument_order['field'], 'op': direction,
                                 'nullsfirst': argument_order.get('nullsfirst', False),
                                 'nullslast': argument_order.get('nullslast', False)})

    # Create Alchemy Filters
    alchemy_filters = []
    for argument_filter in argument_filters:

        # Resolve right attribute
        if "field" in argument_filter.keys():
            right = getattr(instance, argument_filter["field"])
        elif "val" in argument_filter.keys():
            right = argument_filter["val"]
        elif "value" in argument_filter.keys():  # Because we hate abbr sometimes ...
            right = argument_filter["value"]
        else:
            right = None

        # Operator
        op = argument_filter["op"]

        # Resolve left attribute
        if "name" not in argument_filter:
            raise IllegalArgumentError("Missing fieldname attribute 'name'")

        if "__" in argument_filter["name"] or "." in argument_filter["name"]:
            relation, _, name = argument_filter["name"].replace("__", ".").partition(".")
            left = getattr(instance, relation)
            op = "has"
            argument_filter["name"] = name
            right = to_filter(instance=left.property.mapper.class_, filters=[argument_filter])
        elif argument_filter["name"] == "~":
            left = instance
            op = "attr_is"
        else:
            left = getattr(instance, argument_filter["name"])

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
        elif op in ["has"] and isinstance(right, list):
            alchemy_filters.append(left.any(*right))
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
        elif op in ["asc", "desc"]:
            if argument_filter.get("nullsfirst", False):
                alchemy_filters.append(getattr(left, op)().nullsfirst())
            elif argument_filter.get("nullslast", False):
                alchemy_filters.append(getattr(left, op)().nullslast())
            else:
                alchemy_filters.append(getattr(left, op)())

        # Additional Checks
        elif op in ["attr_is"]:
            alchemy_filters.append(getattr(left, right))
        elif op in ["method_is"]:
            alchemy_filters.append(getattr(left, right)())

        # Test comparator
        elif hasattr(left.comparator, op):
            alchemy_filters.append(getattr(left.comparator, op)(right))

        # Raise Exception
        else:
            raise IllegalArgumentError("Unknown operator")
    return alchemy_filters


def to_deep(include,
            exclude,
            key):
    """
        Extract the include/exclude information for key

        :param include: Columns and Relations that should be included for an instance
        :param exclude: Columns and Relations that should not be included for an instance
        :param key: The key that should be extracted
    """
    rtn = {}

    try:
        rtn['include'] = include.setdefault(key, False)
    except AttributeError:
        rtn['include'] = False

    try:
        rtn['exclude'] = exclude[key]
    except TypeError:
        rtn['exclude'] = None

    return rtn


def to_dict(instance,
            options=collections.defaultdict(bool),
            include=None,
            exclude=None):
    """
        Translates sqlalchemy instance to dictionary

        Inspired by flask-restless.helpers.to_dict

        :param instance:
        :param options: Dictionary of flags
                          * execute_queries: Execute Query Objects
                          * execute_hybrids: Execute Hybrids
        :param include: Columns and Relations that should be included for an instance
        :param exclude: Columns and Relations that should not be included for an instance
    """
    if exclude is not None and include is not None:
        raise ValueError('Cannot specify both include and exclude.')

    # None
    if instance is None:
        return None

    # Int / Float / Str
    if isinstance(instance, __basetypes__):
        return instance

    # Date & Time
    if isinstance(instance, __datetypes__):
        return instance.isoformat()

    # Any Dictionary
    if isinstance(instance, dict) or hasattr(instance, 'items'):
        return {k: to_dict(v, options=options, **to_deep(include, exclude, k)) for k, v in instance.items()}

    # Any List
    if isinstance(instance, list) or hasattr(instance, '__iter__'):
        return [to_dict(x, options=options, include=include, exclude=exclude) for x in instance]

    # Include Columns given
    if isinstance(include, collections.Iterable):
        rtn = {}
        for column in include:
            rtn[column] = to_dict(getattr(instance, column), **to_deep(include, exclude, column))
        return rtn

    # Include all columns if it is a SQLAlchemy instance
    try:
        columns = ModelWrapper.get_columns(object_mapper(instance)).keys()
        relations = ModelWrapper.get_relations(object_mapper(instance)).keys()
        attributes = ModelWrapper.get_attributes(object_mapper(instance)).keys()
        proxies = [p.key for p in ModelWrapper.get_proxies(object_mapper(instance))]
        hybrids = [p.key for p in ModelWrapper.get_hybrids(object_mapper(instance))]
        attributes = itertools.chain(columns, relations, proxies, hybrids, attributes)
    except UnmappedInstanceError:
        raise DictConvertionError("Could not convert argument to plain dict")

    rtn = {}

    # Include AssociationProxy and Hybrids (may be list/dict/col)
    for column in attributes:

        if exclude is not None and column in exclude:
            continue
        if column in rtn:
            continue

        # Prevent unnec. db calls
        if include is False and column not in hybrids and column not in columns:
            continue

        if column not in instance.__dict__ and not options.get('execute_queries', True):
            if column not in hybrids or not options.get('execute_hybrids', True):
                continue

        # Get Attribute
        node = getattr(instance, column)

        # Don't execute queries if stopping deepnes
        if include is False and isinstance(node, Query):
            continue
        # Otherwise query it
        elif isinstance(node, Query) and options['execute_queries']:
            node = node.all()

        # Convert it
        rtn[column] = to_dict(node, **to_deep(include, exclude, column))
    return rtn