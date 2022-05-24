from copy import deepcopy
from dataclasses import dataclass

import pytest

from nb_open_prescribing.model import (
    ApiJsonResponse,
    Feature,
    FeatureCollection,
    SpendByCCG,
)


@dataclass
class MockRequestsResponse:
    content: ApiJsonResponse

    def json(self) -> ApiJsonResponse:
        return deepcopy(self.content)


@pytest.fixture
def mock_api_search_response(mocker, response_fixture, request):
    """Fixture to mock API response from HTTP GET request.

    Examples:
        @pytest.mark.usefixtures("mock_api_search_response")
        @pytest.mark.parametrize(
            "response,other_parameters",
                [
                    # Your parameters
                ]
        )
        def test_me(other_parameters):
            ...

    Be aware of the exact name of the parameter, it will get passed to the fixture.
    """
    mocker.patch(
        "nb_open_prescribing.api.OpenPrescribingHttpApi._search",
        return_value=MockRequestsResponse(request.getfixturevalue(response_fixture)),
    )


@pytest.fixture
def spend_by_ccg() -> list[SpendByCCG]:
    return [
        {
            "items": 10,
            "quantity": 10_000,
            "actual_cost": 1000.00,
            "date": "2022-01-01",
            "row_id": "fake",
            "row_name": "fake",
        }
    ]


FEATURE_TEST_DATA: Feature = {
    "type": "Feature",
    "properties": {
        "name": "Someplace Somewhere",
        "code": "DEADBEEF",
        "ons_code": None,
        "org_type": "ABC",
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[1, 100]]],
    },
}


@pytest.fixture
def feature_collection() -> FeatureCollection:
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [FEATURE_TEST_DATA],
    }
