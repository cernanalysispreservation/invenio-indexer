# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utility functions for data processing."""

import os

from flask import current_app
from invenio_search import current_search
from invenio_search.utils import build_index_from_parts


def schema_to_index(schema, index_names=None):
    """Get index given a schema URL.

    :param schema: The schema name
    :param index_names: A list of index name.
    :returns: A tuple containing (index, doc_type).
    """
    parts = schema.split('/')
    doc_type, ext = os.path.splitext(parts[-1])
    parts[-1] = doc_type

    if ext not in {'.json', }:
        return None

    if index_names is None:
        return build_index_from_parts(*parts)

    for start in range(len(parts)):
        name = build_index_from_parts(*parts[start:])
        if name in index_names:
            return name

    return None


def default_record_to_index(record):
    """Get index given a record.

    It tries to extract from `record['$schema']` the index.
    If it fails, return the default value.
    :param record: The record object.
    :returns: The index.
    """
    index_names = current_search.mappings.keys()
    schema = record.get('$schema', '')
    if isinstance(schema, dict):
        schema = schema.get('$ref', '')

    index = schema_to_index(schema, index_names=index_names)

    return index or current_app.config["INDEXER_DEFAULT_INDEX"]
