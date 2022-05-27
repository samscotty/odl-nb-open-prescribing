from collections import ChainMap
from datetime import date
from http import HTTPStatus

import pytest

from nb_open_prescribing.api import OpenPrescribingHttpApi
from nb_open_prescribing.model import (
    CCGBoundaries,
    CCGSpend,
    Feature,
    FeatureCollection,
)


@pytest.fixture
def mock_query_spending_by_ccg_api_response(mocker, spend_json):
    response = mocker.Mock()
    response.json = mocker.Mock(return_value=spend_json)
    response.status_code = HTTPStatus
    yield mocker.patch(
        "nb_open_prescribing.api.OpenPrescribingHttpApi._search",
        return_value=response,
    )


def test_query_spending_by_ccg(mock_query_spending_by_ccg_api_response):
    api = OpenPrescribingHttpApi()
    assert api.query_spending_by_ccg() == [
        CCGSpend(
            items=600,
            quantity=10000.0,
            actual_cost=12345.67,
            date=date(2022, 1, 1),
            row_id="ABC",
            row_name="ANOTHER CCG",
        ),
        CCGSpend(
            items=700,
            quantity=20250.0,
            actual_cost=23456.78,
            date=date(2022, 2, 1),
            row_id="ABC",
            row_name="ANOTHER CCG",
        ),
        CCGSpend(
            items=800,
            quantity=30500.0,
            actual_cost=34567.89,
            date=date(2022, 3, 1),
            row_id="ABC",
            row_name="ANOTHER CCG",
        ),
    ]


@pytest.fixture
def mock_query_org_location_api_response(mocker, boundaries_json):
    response = mocker.Mock()
    response.json = mocker.Mock(return_value=boundaries_json)
    response.status_code = HTTPStatus
    yield mocker.patch(
        "nb_open_prescribing.api.OpenPrescribingHttpApi._search",
        return_value=response,
    )


FEATURE_TEST_JSON_DATA: Feature = {
    "type": "Feature",
    "properties": {
        "name": "NICE PLACE",
        "code": "DEADBEEF",
        "ons_code": None,
        "org_type": "ABC",
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-0.495026, 52.640236],
                [-0.517397, 52.642379],
                [-0.540261, 52.625966],
                [-0.552939, 52.601349],
                [-0.544174, 52.592888],
                [-0.558118, 52.594484],
                [-0.571904, 52.585803],
                [-0.581547, 52.595868],
                [-0.586973, 52.587429],
                [-0.603019, 52.588591],
            ]
        ],
    },
}

FEATURE_COLLECTION_TEST_JSON_DATA: FeatureCollection = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "ABCD:1234"}},
    "features": [FEATURE_TEST_JSON_DATA],
}


def test_query_org_location(mock_query_org_location_api_response):
    api = OpenPrescribingHttpApi()
    actual = api.query_org_location()
    expected = CCGBoundaries(FEATURE_COLLECTION_TEST_JSON_DATA)
    assert actual.crs == expected.crs
    assert actual.features == expected.features


@pytest.fixture
def mock_requests_response(mocker):
    response = mocker.Mock()
    response.json = mocker.Mock(return_value=FEATURE_COLLECTION_TEST_JSON_DATA)
    response.status_code = HTTPStatus
    response.raise_for_status = mocker.Mock(return_value=None)
    yield mocker.patch(
        "requests.Session.get",
        return_value=response,
    )


def test__search_query_construction(mock_requests_response):
    api = OpenPrescribingHttpApi()
    api.query_org_location()
    mock_requests_response.assert_called_once_with(
        "https://openprescribing.net/api/1.0/org_location",
        params=ChainMap({"format": "json"}),
    )


def test__search_handles_api_params(mock_requests_response):
    api = OpenPrescribingHttpApi()
    api.query_org_location(api_params={"add": "me"})
    mock_requests_response.assert_called_once_with(
        "https://openprescribing.net/api/1.0/org_location",
        params=ChainMap({"format": "json"}, {"add": "me"}),
    )


def test__search_handles_api_params_json_format(mock_requests_response):
    api = OpenPrescribingHttpApi()
    api.query_org_location(api_params={"format": "csv", "still": "json"})
    mock_requests_response.assert_called_once_with(
        "https://openprescribing.net/api/1.0/org_location",
        params=ChainMap({"format": "json"}, {"format": "csv", "still": "json"}),
    )
