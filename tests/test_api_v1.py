# SPDX-License-Identifier: GPL-3.0-or-later
import io
import json
import os
import tarfile
from unittest import mock

import pytest

from cachito.workers.tasks import fetch_app_source, fetch_gomod_source, assemble_source_code_archive


def test_ping(client):
    rv = client.get('/api/v1/ping')
    assert json.loads(rv.data.decode('utf-8')) is True


@mock.patch('cachito.web.api_v1.chain')
def test_create_and_fetch_request(mock_chain, client, db):
    data = {
        'repo': 'https://github.com/release-engineering/retrodep.git',
        'ref': 'c50b93a32df1c9d700e3e80996845bc2e13be848',
        'pkg_managers': ['gomod']
    }

    rv = client.post('/api/v1/requests', json=data)
    assert rv.status_code == 201
    created_request = json.loads(rv.data.decode('utf-8'))
    for key, expected_value in data.items():
        assert expected_value == created_request[key]

    mock_chain.assert_called_once_with(
        fetch_app_source.s(
            'https://github.com/release-engineering/retrodep.git',
            'c50b93a32df1c9d700e3e80996845bc2e13be848'),
        fetch_gomod_source.s()
    )

    request_id = created_request['id']
    rv = client.get('/api/v1/requests/{}'.format(request_id))
    assert rv.status_code == 200
    fetched_request = json.loads(rv.data.decode('utf-8'))

    assert created_request == fetched_request
    assert fetched_request['state'] == 'in_progress'
    assert fetched_request['state_reason'] == 'The request was initiated'


@mock.patch('cachito.web.api_v1.chain')
def test_fetch_paginated_requests(mock_chain, client, db):

    repo_template = 'https://github.com/release-engineering/retrodep{}.git'
    for i in range(50):
        data = {
            'repo': repo_template.format(i),
            'ref': 'c50b93a32df1c9d700e3e80996845bc2e13be848',
            'pkg_managers': ['gomod']
        }

        rv = client.post('/api/v1/requests', json=data)
        assert rv.status_code == 201

    # Sane defaults are provided
    rv = client.get('/api/v1/requests')
    assert rv.status_code == 200
    response = json.loads(rv.data.decode('utf-8'))
    fetched_requests = response['items']
    assert len(fetched_requests) == 20
    for repo_number, request in enumerate(fetched_requests):
        assert request['repo'] == repo_template.format(repo_number)

    # per_page and page parameters are honored
    rv = client.get('/api/v1/requests?page=2&per_page=10')
    assert rv.status_code == 200
    response = json.loads(rv.data.decode('utf-8'))
    fetched_requests = response['items']
    assert len(fetched_requests) == 10
    # Start at 10 because each page contains 10 items and we're processing the second page
    for repo_number, request in enumerate(fetched_requests, 10):
        assert request['repo'] == repo_template.format(repo_number)


def test_create_and_fetch_request_invalid_ref(client, db):
    data = {
        'repo': 'https://github.com/release-engineering/retrodep.git',
        'ref': 'not-a-ref',
        'pkg_managers': ['gomod']
    }

    rv = client.post('/api/v1/requests', json=data)
    assert rv.status_code == 400
    error = json.loads(rv.data.decode('utf-8'))
    assert error['error'] == 'The "ref" parameter must be a 40 character hex string'


def test_missing_request(client, db):
    rv = client.get('/api/v1/requests/1')
    assert rv.status_code == 404

    rv = client.get('/api/v1/requests/1/download')
    assert rv.status_code == 404


def test_malformed_request_id(client, db):
    rv = client.get('/api/v1/requests/spam')
    assert rv.status_code == 404
    data = json.loads(rv.data.decode('utf-8'))
    assert data == {'error': 'The requested resource was not found'}


@pytest.mark.parametrize('removed_params', (
    ('repo', 'ref', 'pkg_managers'),
    ('repo',),
    ('ref',),
    ('pkg_managers',),
))
def test_validate_required_params(client, db, removed_params):
    data = {
        'repo': 'https://github.com/release-engineering/retrodep.git',
        'ref': 'c50b93a32df1c9d700e3e80996845bc2e13be848',
        'pkg_managers': ['gomod']
    }
    for removed_param in removed_params:
        data.pop(removed_param)

    rv = client.post('/api/v1/requests', json=data)
    assert rv.status_code == 400
    error_msg = json.loads(rv.data.decode('utf-8'))['error']
    assert 'Missing required' in error_msg
    for removed_param in removed_params:
        assert removed_param in error_msg


def test_validate_extraneous_params(client, db):
    data = {
        'repo': 'https://github.com/release-engineering/retrodep.git',
        'ref': 'c50b93a32df1c9d700e3e80996845bc2e13be848',
        'pkg_managers': ['gomod'],
        'spam': 'maps',
    }

    rv = client.post('/api/v1/requests', json=data)
    assert rv.status_code == 400
    error_msg = json.loads(rv.data.decode('utf-8'))['error']
    assert 'invalid keyword argument' in error_msg
    assert 'spam' in error_msg


@mock.patch('tempfile.TemporaryDirectory')
@mock.patch('cachito.web.api_v1.Request')
@mock.patch('cachito.web.api_v1.chain')
def test_download_archive(
    mock_chain, mock_request, mock_temp_dir, client, db, app, tmpdir
):
    ephemeral_dir_name = 'ephemeral123'
    shared_cachito_dir = tmpdir
    shared_temp_dir = shared_cachito_dir.mkdir(ephemeral_dir_name)
    mock_temp_dir.return_value.__enter__.return_value = str(shared_temp_dir)

    bundle_archive_contents = {
        'app/spam.go': b'Spam mapS',
        'app/ham.go': b'Ham maH',
        'gomod/pkg/mod/cache/download/server.com/dep1/@v/dep1.zip': b'dep1 archive',
        'gomod/pkg/mod/cache/download/server.com/dep2/@v/dep2.zip': b'dep2 archive',
    }
    bundle_archive_path = shared_temp_dir.join('bundle.tar.gz')

    def chain_side_effect(*args, **kwargs):
        # Create mocked bundle source code archive
        with tarfile.open(bundle_archive_path, mode='w:gz') as bundle_archive:
            for name, data in bundle_archive_contents.items():
                fileobj = io.BytesIO(data)
                tarinfo = tarfile.TarInfo(name)
                tarinfo.size = len(fileobj.getvalue())
                bundle_archive.addfile(tarinfo, fileobj=fileobj)
        return mock.Mock()

    mock_chain.side_effect = chain_side_effect

    with mock.patch.dict(app.config, {'CACHITO_SHARED_DIR': str(shared_cachito_dir)}):
        rv = client.get('/api/v1/requests/1/download')

    # Verify chain was called correctly.
    mock_chain.assert_called_once_with(
        fetch_app_source.s(
            mock_request.query.get_or_404().repo, mock_request.query.get_or_404().ref,
        ),
        fetch_gomod_source.s(copy_cache_to=os.path.join(ephemeral_dir_name, 'deps')),
        assemble_source_code_archive.s(
            deps_path=os.path.join(ephemeral_dir_name, 'deps'),
            bundle_archive_path=os.path.join(ephemeral_dir_name, 'bundle.tar.gz')),
    )

    # Verify contents of downloaded archive
    with tarfile.open(fileobj=io.BytesIO(rv.data), mode='r:*') as bundle_archive:
        for expected_member in list(bundle_archive_contents.keys()):
            bundle_archive.getmember(expected_member)
