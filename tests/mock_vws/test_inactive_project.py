"""
Tests for inactive projects.
"""

import pytest

from tests.mock_vws.utils import assert_vws_failure, Endpoint
from tests.utils import VuforiaServerCredentials
from vws.request_utils import target_api_request


@pytest.mark.usefixtures('verify_mock_vuforia_inactive')
class TestInactiveProject:
    """
    Tests for inactive projects.
    """

    def test_inactive_project(
        self,
        endpoint: Endpoint,
        vuforia_inactive_server_credentials: VuforiaServerCredentials,
    ) -> None:
        """
        A response for an inactive project describes that the project is
        inactive.
        """
        response = target_api_request(
            access_key=vuforia_inactive_server_credentials.access_key,
            secret_key=vuforia_inactive_server_credentials.secret_key,
            method=endpoint.method,
            content=endpoint.content,
            request_path=endpoint.example_path,
        )

        assert_vws_failure(
            response=response,
            status_code='X',
            result_code='X',
        )
