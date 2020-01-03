"""
Choose which backends to use for the tests.
"""

import logging
import os
from typing import Generator

import pytest
from _pytest.fixtures import SubRequest
from requests import codes

from mock_vws import MockVWS
from mock_vws._constants import ResultCodes
from mock_vws.database import VuforiaDatabase
from mock_vws.states import States
from tests.mock_vws.utils import (
    delete_target,
    list_targets,
    update_target,
    wait_for_target_processed,
)
from tests.mock_vws.utils.assertions import assert_vws_response

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def _delete_all_targets(database_keys: VuforiaDatabase) -> None:
    """
    Delete all targets.

    Args:
        database_keys: The credentials to the Vuforia target database to delete
            all targets in.
    """
    response = list_targets(vuforia_database=database_keys)

    if 'results' not in response.json():  # pragma: no cover
        message = f'Results not found.\nResponse is: {response.json()}'
        LOGGER.debug(message)

    targets = response.json()['results']

    for target in targets:
        wait_for_target_processed(
            vuforia_database=database_keys,
            target_id=target,
        )

        # Even deleted targets can be matched by a query for a few seconds so
        # we change the target to inactive before deleting it.
        update_target(
            vuforia_database=database_keys,
            data={'active_flag': False},
            target_id=target,
        )
        wait_for_target_processed(
            vuforia_database=database_keys,
            target_id=target,
        )
        response = delete_target(
            vuforia_database=database_keys,
            target_id=target,
        )
        assert_vws_response(
            response=response,
            status_code=codes.OK,
            result_code=ResultCodes.SUCCESS,
        )


@pytest.fixture(params=[True, False], ids=['Real Vuforia', 'Mock Vuforia'])
def verify_mock_vuforia(
    request: SubRequest,
    vuforia_database: VuforiaDatabase,
    inactive_database: VuforiaDatabase,
) -> Generator:
    """
    Test functions which use this fixture are run twice. Once with the real
    Vuforia, and once with the mock.

    This is useful for verifying the mock.
    """
    skip_real = os.getenv('SKIP_REAL') == '1'
    skip_mock = os.getenv('SKIP_MOCK') == '1'

    use_real_vuforia = request.param

    if use_real_vuforia and skip_real:  # pragma: no cover
        pytest.skip()

    if not use_real_vuforia and skip_mock:  # pragma: no cover
        pytest.skip()

    working_database = VuforiaDatabase(
        database_name=vuforia_database.database_name,
        server_access_key=vuforia_database.server_access_key,
        server_secret_key=vuforia_database.server_secret_key,
        client_access_key=vuforia_database.client_access_key,
        client_secret_key=vuforia_database.client_secret_key,
    )

    inactive_database = VuforiaDatabase(
        state=States.PROJECT_INACTIVE,
        database_name=inactive_database.database_name,
        server_access_key=inactive_database.server_access_key,
        server_secret_key=inactive_database.server_secret_key,
        client_access_key=inactive_database.client_access_key,
        client_secret_key=inactive_database.client_secret_key,
    )
    if use_real_vuforia:
        _delete_all_targets(database_keys=vuforia_database)
        yield
    else:
        with MockVWS(processing_time_seconds=0.2) as mock:
            mock.add_database(database=working_database)
            mock.add_database(database=inactive_database)
            yield
