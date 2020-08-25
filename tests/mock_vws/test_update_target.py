"""
Tests for the mock of the update target endpoint.
"""

import base64
import io
import uuid
from http import HTTPStatus
from typing import Any, Union

import pytest
from vws import VWS
from vws.exceptions import ProjectInactive

from mock_vws._constants import ResultCodes, TargetStatuses
from mock_vws.database import VuforiaDatabase
from tests.mock_vws.utils import (
    add_target_to_vws,
    make_image_file,
    update_target,
)
from tests.mock_vws.utils.assertions import (
    assert_vws_failure,
    assert_vws_response,
)


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestUpdate:
    """
    Tests for updating targets.
    """

    @pytest.mark.parametrize(
        'content_type',
        [
            # This is the documented required content type:
            'application/json',
            # Other content types also work.
            'other/content_type',
        ],
        ids=['Documented Content-Type', 'Undocumented Content-Type'],
    )
    def test_content_types(
        self,
        vuforia_database: VuforiaDatabase,
        image_file_failed_state: io.BytesIO,
        content_type: str,
    ) -> None:
        """
        The ``Content-Type`` header does not change the response as long as it
        is not empty.
        """
        image_data = image_file_failed_state.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        data = {
            'name': 'example',
            'width': 1,
            'image': image_data_encoded,
        }

        response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=data,
        )

        target_id = response.json()['target_id']

        response = update_target(
            vuforia_database=vuforia_database,
            data={'name': 'Adam'},
            target_id=target_id,
            content_type=content_type,
        )

        # Code is FORBIDDEN because the target is processing.
        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.FORBIDDEN,
            result_code=ResultCodes.TARGET_STATUS_NOT_SUCCESS,
        )

    def test_empty_content_type(
        self,
        vuforia_database: VuforiaDatabase,
        image_file_failed_state: io.BytesIO,
    ) -> None:
        """
        An ``UNAUTHORIZED`` response is given if an empty ``Content-Type``
        header is given.
        """
        image_data = image_file_failed_state.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        data = {
            'name': 'example',
            'width': 1,
            'image': image_data_encoded,
        }

        response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=data,
        )

        target_id = response.json()['target_id']

        response = update_target(
            vuforia_database=vuforia_database,
            data={'name': 'Adam'},
            target_id=target_id,
            content_type='',
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNAUTHORIZED,
            result_code=ResultCodes.AUTHENTICATION_FAILURE,
        )

    def test_no_fields_given(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        No data fields are required.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )

        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

        assert response.json().keys() == {'result_code', 'transaction_id'}

        target_details = vws_client.get_target_record(target_id=target_id)
        # Targets go back to processing after being updated.
        assert target_details.status.value == TargetStatuses.PROCESSING.value

        vws_client.wait_for_target_processed(target_id=target_id)

        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.status.value == TargetStatuses.SUCCESS.value


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestUnexpectedData:
    """
    Tests for passing data which is not allowed to the endpoint.
    """

    def test_invalid_extra_data(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        A `BAD_REQUEST` response is returned when unexpected data is given.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'extra_thing': 1},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            result_code=ResultCodes.FAIL,
        )


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestWidth:
    """
    Tests for the target width field.
    """

    @pytest.mark.parametrize(
        'width',
        [-1, '10', None, 0],
        ids=['Negative', 'Wrong Type', 'None', 'Zero'],
    )
    def test_width_invalid(
        self,
        vuforia_database: VuforiaDatabase,
        width: Any,
        target_id: str,
    ) -> None:
        """
        The width must be a number greater than zero.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        target_details = vws_client.get_target_record(target_id=target_id)
        original_width = target_details.target_record.width

        response = update_target(
            vuforia_database=vuforia_database,
            data={'width': width},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            result_code=ResultCodes.FAIL,
        )

        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.target_record.width == original_width

    def test_width_valid(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        Positive numbers are valid widths.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        width = 0.01

        response = update_target(
            vuforia_database=vuforia_database,
            data={'width': width},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.target_record.width == width


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestActiveFlag:
    """
    Tests for the active flag parameter.
    """

    @pytest.mark.parametrize('initial_active_flag', [True, False])
    @pytest.mark.parametrize('desired_active_flag', [True, False])
    def test_active_flag(
        self,
        vuforia_database: VuforiaDatabase,
        image_file_success_state_low_rating: io.BytesIO,
        initial_active_flag: bool,
        desired_active_flag: bool,
    ) -> None:
        """
        Setting the active flag to a Boolean value changes it.
        """
        image_data = image_file_success_state_low_rating.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        data = {
            'name': 'example',
            'width': 1,
            'image': image_data_encoded,
            'active_flag': initial_active_flag,
        }

        response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=data,
        )

        target_id = response.json()['target_id']

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'active_flag': desired_active_flag},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.target_record.active_flag == desired_active_flag

    @pytest.mark.parametrize('desired_active_flag', ['string', None])
    def test_invalid(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        desired_active_flag: Union[str, None],
    ) -> None:
        """
        Values which are not Boolean values are not valid active flags.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'active_flag': desired_active_flag},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            result_code=ResultCodes.FAIL,
        )


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestApplicationMetadata:
    """
    Tests for the application metadata parameter.
    """

    _MAX_METADATA_BYTES = 1024 * 1024 - 1

    @pytest.mark.parametrize(
        'metadata',
        [
            b'a',
            b'a' * _MAX_METADATA_BYTES,
        ],
        ids=['Short', 'Max length'],
    )
    def test_base64_encoded(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        metadata: bytes,
    ) -> None:
        """
        A base64 encoded string is valid application metadata.
        """
        metadata_encoded = base64.b64encode(metadata).decode('ascii')

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'application_metadata': metadata_encoded},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

    @pytest.mark.parametrize('invalid_metadata', [1, None])
    def test_invalid_type(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        invalid_metadata: Union[int, None],
    ) -> None:
        """
        Non-string values cannot be given as valid application metadata.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'application_metadata': invalid_metadata},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            result_code=ResultCodes.FAIL,
        )

    def test_not_base64_encoded_processable(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        not_base64_encoded_processable: str,
    ) -> None:
        """
        Some strings which are not valid base64 encoded strings are allowed as
        application metadata.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'application_metadata': not_base64_encoded_processable},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

    def test_not_base64_encoded_not_processable(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        not_base64_encoded_not_processable: str,
    ) -> None:
        """
        Some strings which are not valid base64 encoded strings are not allowed
        as application metadata.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'application_metadata': not_base64_encoded_not_processable},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.FAIL,
        )

    def test_metadata_too_large(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        A base64 encoded string of greater than 1024 * 1024 bytes is too large
        for application metadata.
        """
        metadata = b'a' * (self._MAX_METADATA_BYTES + 1)
        metadata_encoded = base64.b64encode(metadata).decode('ascii')

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'application_metadata': metadata_encoded},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.METADATA_TOO_LARGE,
        )


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestTargetName:
    """
    Tests for the target name field.
    """

    _MAX_CHAR_VALUE = 65535
    _MAX_NAME_LENGTH = 64

    @pytest.mark.parametrize(
        'name',
        [
            'á',
            # We test just below the max character value.
            # This is because targets with the max character value in their
            # names get stuck in the processing stage.
            chr(_MAX_CHAR_VALUE - 2),
            'a' * _MAX_NAME_LENGTH,
        ],
        ids=['Short name', 'Max char value', 'Long name'],
    )
    def test_name_valid(
        self,
        name: str,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        A target's name must be a string of length 0 < N < 65.

        We test characters out of range in another test as that gives a
        different error.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)
        vws_client.update_target(target_id=target_id, name=name)
        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.target_record.name == name

    @pytest.mark.parametrize(
        'name,status_code,result_code',
        [
            (1, HTTPStatus.BAD_REQUEST, ResultCodes.FAIL),
            ('', HTTPStatus.BAD_REQUEST, ResultCodes.FAIL),
            (
                'a' * (_MAX_NAME_LENGTH + 1),
                HTTPStatus.BAD_REQUEST,
                ResultCodes.FAIL,
            ),
            (None, HTTPStatus.BAD_REQUEST, ResultCodes.FAIL),
            (
                chr(_MAX_CHAR_VALUE + 1),
                HTTPStatus.FORBIDDEN,
                ResultCodes.TARGET_NAME_EXIST,
            ),
            (
                chr(_MAX_CHAR_VALUE + 1) * (_MAX_NAME_LENGTH + 1),
                HTTPStatus.BAD_REQUEST,
                ResultCodes.FAIL,
            ),
        ],
        ids=[
            'Wrong Type',
            'Empty',
            'Too Long',
            'None',
            'Bad char',
            'Bad char too long',
        ],
    )
    def test_name_invalid(
        self,
        name: str,
        target_id: str,
        vuforia_database: VuforiaDatabase,
        status_code: int,
        result_code: ResultCodes,
    ) -> None:
        """
        A target's name must be a string of length 0 < N < 65.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'name': name},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=status_code,
            result_code=result_code,
        )

    def test_existing_target_name(
        self,
        image_file_success_state_low_rating: io.BytesIO,
        vuforia_database: VuforiaDatabase,
    ) -> None:
        """
        Only one target can have a given name.
        """
        image_data = image_file_success_state_low_rating.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        first_target_name = 'example_name'
        second_target_name = 'another_example_name'

        data = {
            'name': first_target_name,
            'width': 1,
            'image': image_data_encoded,
        }

        response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=data,
        )

        first_target_id = response.json()['target_id']

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )

        other_data = {
            'name': second_target_name,
            'width': 1,
            'image': image_data_encoded,
        }

        response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=other_data,
        )

        second_target_id = response.json()['target_id']

        vws_client.wait_for_target_processed(target_id=first_target_id)
        vws_client.wait_for_target_processed(target_id=second_target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'name': first_target_name},
            target_id=second_target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.FORBIDDEN,
            result_code=ResultCodes.TARGET_NAME_EXIST,
        )

    def test_same_name_given(
        self,
        image_file_success_state_low_rating: io.BytesIO,
        vuforia_database: VuforiaDatabase,
    ) -> None:
        """
        Updating a target with its own name does not give an error.
        """
        image_data = image_file_success_state_low_rating.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        name = 'example'

        data = {
            'name': name,
            'width': 1,
            'image': image_data_encoded,
        }

        response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=data,
        )

        target_id = response.json()['target_id']

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'name': name},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.target_record.name == name


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestImage:
    """
    Tests for the image parameter.

    The specification for images is documented in "Supported Images" on
    https://library.vuforia.com/articles/Training/Image-Target-Guide
    """

    def test_image_valid(
        self,
        vuforia_database: VuforiaDatabase,
        image_files_failed_state: io.BytesIO,
        target_id: str,
    ) -> None:
        """
        JPEG and PNG files in the RGB and greyscale color spaces are allowed.
        """
        image_file = image_files_failed_state
        image_data = image_file.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': image_data_encoded},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

    def test_bad_image_format_or_color_space(
        self,
        bad_image_file: io.BytesIO,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        A `BAD_REQUEST` response is returned if an image which is not a JPEG
        or PNG file is given, or if the given image is not in the greyscale or
        RGB color space.
        """
        image_data = bad_image_file.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': image_data_encoded},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.BAD_IMAGE,
        )

    def test_corrupted(
        self,
        vuforia_database: VuforiaDatabase,
        corrupted_image_file: io.BytesIO,
        target_id: str,
    ) -> None:
        """
        No error is returned when the given image is corrupted.
        """
        image_data = corrupted_image_file.getvalue()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': image_data_encoded},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

    def test_image_too_large(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        An `ImageTooLarge` result is returned if the image is above a certain
        threshold.
        """
        max_bytes = 2.3 * 1024 * 1024
        width = height = 886
        png_not_too_large = make_image_file(
            file_format='PNG',
            color_space='RGB',
            width=width,
            height=height,
        )

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        image_data = png_not_too_large.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')
        image_content_size = len(image_data)
        # We check that the image we created is just slightly smaller than the
        # maximum file size.
        #
        # This is just because of the implementation details of
        # ``max_image_file``.
        assert image_content_size < max_bytes
        assert (image_content_size * 1.05) > max_bytes

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': image_data_encoded},
            target_id=target_id,
        )

        assert_vws_response(
            response=response,
            status_code=HTTPStatus.OK,
            result_code=ResultCodes.SUCCESS,
        )

        vws_client.wait_for_target_processed(target_id=target_id)

        width = width + 1
        height = height + 1
        png_too_large = make_image_file(
            file_format='PNG',
            color_space='RGB',
            width=width,
            height=height,
        )

        image_data = png_too_large.read()
        image_data_encoded = base64.b64encode(image_data).decode('ascii')
        image_content_size = len(image_data)
        # We check that the image we created is just slightly smaller than the
        # maximum file size.
        #
        # This is just because of the implementation details of
        # ``max_image_file``.
        assert image_content_size < max_bytes
        assert (image_content_size * 1.05) > max_bytes

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': image_data_encoded},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.IMAGE_TOO_LARGE,
        )

    def test_not_base64_encoded_processable(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        not_base64_encoded_processable: str,
    ) -> None:
        """
        Some strings which are not valid base64 encoded strings are allowed as
        an image without getting a "Fail" response.
        This is because Vuforia treats them as valid base64, but then not a
        valid image.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': not_base64_encoded_processable},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.BAD_IMAGE,
        )

    def test_not_base64_encoded_not_processable(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
        not_base64_encoded_not_processable: str,
    ) -> None:
        """
        Some strings which are not valid base64 encoded strings are not
        processable by Vuforia, and then when given as an image Vuforia returns
        a "Fail" response.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': not_base64_encoded_not_processable},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.FAIL,
        )

    def test_not_image(
        self,
        vuforia_database: VuforiaDatabase,
        target_id: str,
    ) -> None:
        """
        If the given image is not an image file then a `BadImage` result is
        returned.
        """
        not_image_data = b'not_image_data'
        image_data_encoded = base64.b64encode(not_image_data).decode('ascii')

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': image_data_encoded},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            result_code=ResultCodes.BAD_IMAGE,
        )

    @pytest.mark.parametrize('invalid_type_image', [1, None])
    def test_invalid_type(
        self,
        invalid_type_image: Union[int, None],
        target_id: str,
        vuforia_database: VuforiaDatabase,
    ) -> None:
        """
        If the given image is not a string, a `Fail` result is returned.
        """
        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        response = update_target(
            vuforia_database=vuforia_database,
            data={'image': invalid_type_image},
            target_id=target_id,
        )

        assert_vws_failure(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            result_code=ResultCodes.FAIL,
        )

    def test_rating_can_change(
        self,
        image_file_success_state_low_rating: io.BytesIO,
        high_quality_image: io.BytesIO,
        vuforia_database: VuforiaDatabase,
    ) -> None:
        """
        If the target is updated with an image of different quality, the
        tracking rating can change.

        "quality" refers to Vuforia's internal rating system.
        The mock randomly assigns a quality and makes sure that the new quality
        is different to the old quality.
        """
        poor_image = image_file_success_state_low_rating.read()
        poor_image_data_encoded = base64.b64encode(poor_image).decode('ascii')

        good_image = high_quality_image.read()
        good_image_data_encoded = base64.b64encode(good_image).decode('ascii')

        data = {
            'name': 'example',
            'width': 1,
            'image': poor_image_data_encoded,
        }

        add_response = add_target_to_vws(
            vuforia_database=vuforia_database,
            data=data,
        )

        target_id = add_response.json()['target_id']

        vws_client = VWS(
            server_access_key=vuforia_database.server_access_key,
            server_secret_key=vuforia_database.server_secret_key,
        )
        vws_client.wait_for_target_processed(target_id=target_id)

        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.status.value == TargetStatuses.SUCCESS.value
        # Tracking rating is between 0 and 5 when status is 'success'
        original_tracking_rating = target_details.target_record.tracking_rating
        assert original_tracking_rating in range(6)

        update_target(
            vuforia_database=vuforia_database,
            data={'image': good_image_data_encoded},
            target_id=target_id,
        )

        vws_client.wait_for_target_processed(target_id=target_id)
        target_details = vws_client.get_target_record(target_id=target_id)
        assert target_details.status.value == TargetStatuses.SUCCESS.value
        # Tracking rating is between 0 and 5 when status is 'success'
        new_tracking_rating = target_details.target_record.tracking_rating
        assert new_tracking_rating in range(6)

        assert original_tracking_rating != new_tracking_rating


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestInactiveProject:
    """
    Tests for inactive projects.
    """

    def test_inactive_project(
        self,
        inactive_database: VuforiaDatabase,
    ) -> None:
        """
        If the project is inactive, a FORBIDDEN response is returned.
        """
        vws_client = VWS(
            server_access_key=inactive_database.server_access_key,
            server_secret_key=inactive_database.server_secret_key,
        )
        with pytest.raises(ProjectInactive):
            vws_client.update_target(target_id=uuid.uuid4().hex)
