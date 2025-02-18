# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2022 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test CLI."""

import uuid

from click.testing import CliRunner
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records import Record
from invenio_search import current_search, current_search_client

from invenio_indexer import cli
from invenio_indexer.api import RecordIndexer


def test_run(app):
    """Test run."""
    runner = app.test_cli_runner()
    res = runner.invoke(cli.run, [])
    assert 0 == res.exit_code

    runner = app.test_cli_runner()
    res = runner.invoke(cli.run, ["-d", "-c", "2"])
    assert 0 == res.exit_code
    assert "Starting 2 tasks" in res.output


def test_reindex(app):
    """Test reindex."""
    # load records
    with app.test_request_context():
        runner = app.test_cli_runner()

        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        record1 = Record.create(dict(title="Test 1", recid=1), id_=id1)
        record2 = Record.create(dict(title="Test 2", recid=2), id_=id2)
        PersistentIdentifier.create(
            pid_type="recid",
            pid_value=1,
            object_type="rec",
            object_uuid=id1,
            status=PIDStatus.REGISTERED,
        )
        PersistentIdentifier.create(
            pid_type="recid",
            pid_value=2,
            object_type="rec",
            object_uuid=id2,
            status=PIDStatus.REGISTERED,
        )
        db.session.commit()
        indexer = RecordIndexer()
        index = indexer.record_to_index(record1)

        # Make sure the index doesn't exist at the beginning (it was not
        # preserved by accident from some other tests)
        assert current_search_client.indices.exists(index) is False

        # Initialize queue
        res = runner.invoke(cli.queue, ["init", "purge"])
        assert 0 == res.exit_code

        res = runner.invoke(cli.reindex, ["--yes-i-know", "-t", "recid"])
        assert 0 == res.exit_code
        res = runner.invoke(cli.run, [])
        assert 0 == res.exit_code
        current_search.flush_and_refresh(index)

        # Both records should be indexed
        res = current_search_client.search(index=index)
        assert len(res["hits"]["hits"]) == 2

        # Delete one of the records
        record2 = Record.get_record(id2)
        record2.delete()
        db.session.commit()
        # Destroy the index and reindex
        list(current_search.delete(ignore=[404]))
        res = runner.invoke(cli.reindex, ["--yes-i-know", "-t", "recid"])
        assert 0 == res.exit_code
        res = runner.invoke(cli.run, [])
        assert 0 == res.exit_code
        current_search.flush_and_refresh(index)

        # Check that the deleted record is not indexed
        res = current_search_client.search(index=index)
        assert len(res["hits"]["hits"]) == 1
        assert res["hits"]["hits"][0]["_source"]["title"] == "Test 1"

        # Destroy queue and the index
        res = runner.invoke(cli.queue, ["delete"])
        assert 0 == res.exit_code
        list(current_search.delete(ignore=[404]))
