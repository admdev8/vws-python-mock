"""
Tests for the mock of the target summary endpoint.
"""

import base64
import datetime
import io

import pytest
from requests import codes

from mock_vws._constants import ResultCodes, TargetStatuses
from tests.mock_vws.utils import (
    add_target_to_vws,
    get_vws_target,
    target_summary,
    wait_for_target_processed,
)
from tests.mock_vws.utils.assertions import assert_vws_response
from tests.mock_vws.utils.authorization import VuforiaDatabaseKeys


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestTargetSummary:
    """
    Tests for the target summary endpoint.
    """

    def test_target_summary(
        self,
        vuforia_database_keys: VuforiaDatabaseKeys,
        png_rgb: io.BytesIO,
    ) -> None:
        """
        A target summary is returned.
        """
        name = 'example target name 1234'

        image_data = png_rgb.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        date_before_add_target = datetime.datetime.now().date()

        target_response = add_target_to_vws(
            vuforia_database_keys=vuforia_database_keys,
            data={
                'name': name,
                'width': 1,
                'image': image_data_encoded,
            },
        )

        target_id = target_response.json()['target_id']

        date_after_add_target = datetime.datetime.now().date()

        response = target_summary(
            vuforia_database_keys=vuforia_database_keys,
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=codes.OK,
            result_code=ResultCodes.SUCCESS,
        )

        expected_keys = {
            'status',
            'result_code',
            'transaction_id',
            'database_name',
            'target_name',
            'upload_date',
            'active_flag',
            'tracking_rating',
            'total_recos',
            'current_month_recos',
            'previous_month_recos',
        }

        assert response.json().keys() == expected_keys
        assert response.json()['status'] == TargetStatuses.PROCESSING.value
        response_database_name = response.json()['database_name']
        assert response_database_name == vuforia_database_keys.database_name
        assert response.json()['target_name'] == name

        # In case the date changes while adding a target
        # we allow the date before and after adding the target.
        assert response.json()['upload_date'] in (
            date_before_add_target.strftime('%Y-%m-%d'),
            date_after_add_target.strftime('%Y-%m-%d'),
        )

        # While processing the tracking rating is -1.
        assert response.json()['tracking_rating'] == -1

    def test_after_processing(
        self,
        vuforia_database_keys: VuforiaDatabaseKeys,
        png_rgb: io.BytesIO,
    ) -> None:
        """
        After processing is completed, the tracking rating is in the range of
        0 to 5.
        """
        image_data = png_rgb.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        target_response = add_target_to_vws(
            vuforia_database_keys=vuforia_database_keys,
            data={
                'name': 'example',
                'width': 1,
                'image': image_data_encoded,
            },
        )

        target_id = target_response.json()['target_id']

        # The tracking rating may change during processing.
        # Therefore we wait until processing ends.
        wait_for_target_processed(
            vuforia_database_keys=vuforia_database_keys,
            target_id=target_id,
        )

        response = target_summary(
            vuforia_database_keys=vuforia_database_keys,
            target_id=target_id,
        )

        get_target_response = get_vws_target(
            vuforia_database_keys=vuforia_database_keys,
            target_id=target_id,
        )

        target_record = get_target_response.json()['target_record']
        tracking_rating = target_record['tracking_rating']
        assert response.json()['tracking_rating'] == tracking_rating
        assert response.json()['tracking_rating'] in range(6)
        assert response.json()['status'] == TargetStatuses.FAILED.value

    @pytest.mark.parametrize('active_flag', [True, False])
    def test_active_flag(
        self,
        vuforia_database_keys: VuforiaDatabaseKeys,
        png_rgb: io.BytesIO,
        active_flag: bool,
    ) -> None:
        """
        The active flag of the target is returned.
        """
        image_data = png_rgb.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        target_response = add_target_to_vws(
            vuforia_database_keys=vuforia_database_keys,
            data={
                'name': 'example',
                'width': 1,
                'image': image_data_encoded,
                'active_flag': active_flag,
            },
        )

        target_id = target_response.json()['target_id']
        response = target_summary(
            vuforia_database_keys=vuforia_database_keys,
            target_id=target_id,
        )
        assert response.json()['active_flag'] == active_flag
