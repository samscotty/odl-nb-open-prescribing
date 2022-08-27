from collections import ChainMap
from http import HTTPStatus

import pytest

from nb_open_prescribing.api import HttpApiDataProvider, OpenPrescribingHttpApi
from nb_open_prescribing.model import (
    CCGBoundaries,
    CCGSpend,
    DrugDetail,
    FeatureCollection,
    SpendingByCCG,
)

SPENDING_BY_CCG_TEST_JSON_DATA: list[SpendingByCCG] = [
    {
        "items": 600,
        "quantity": 10000.0,
        "actual_cost": 12345.67,
        "date": "2022-01-01",
        "row_id": "ABC",
        "row_name": "ANOTHER CCG",
    },
    {
        "items": 700,
        "quantity": 20250.0,
        "actual_cost": 23456.78,
        "date": "2022-02-01",
        "row_id": "ABC",
        "row_name": "ANOTHER CCG",
    },
    {
        "items": 800,
        "quantity": 30500.0,
        "actual_cost": 34567.89,
        "date": "2022-03-01",
        "row_id": "ABC",
        "row_name": "ANOTHER CCG",
    },
]


@pytest.fixture
def mock_query_api_json_response(mocker, request):
    marker = request.node.get_closest_marker("json_response")
    response = mocker.Mock()
    response.json = mocker.Mock(return_value=marker.args[0])
    response.status_code = HTTPStatus
    yield mocker.patch(
        "nb_open_prescribing.api.OpenPrescribingHttpApi._search",
        return_value=response,
    )


@pytest.mark.json_response(SPENDING_BY_CCG_TEST_JSON_DATA)
def test_query_spending_by_ccg(mock_query_api_json_response):
    api = OpenPrescribingHttpApi()
    response = api.query_spending_by_ccg()
    mock_query_api_json_response.assert_called_once()
    assert response == [CCGSpend.from_dict(o) for o in SPENDING_BY_CCG_TEST_JSON_DATA]


DRUG_DETAILS_TEST_JSON_DATA = [
    {
        "type": "BNF chapter",
        "id": "2",
        "name": "Cardiovascular System",
    },
    {
        "type": "BNF section",
        "id": "2.12",
        "name": "Lipid-regulating drugs",
    },
    {
        "type": "BNF paragraph",
        "id": "2.1.2",
        "name": "Phosphodiesterase Type-3 inhibitors",
    },
    {
        "type": "chemical",
        "id": "021200000",
        "name": "Other Lipid-Regulating Preps",
        "section": "2.12: Lipid-regulating drugs",
    },
    {
        "type": "product",
        "id": "0212000F0AA",
        "name": "Colestyramine (Lipid lowering)",
        "is_generic": True,
    },
    {
        "type": "product format",
        "id": "190205500BCNSA0",
        "name": "Avene XeraCalm A.D Lipid-Replenishing balm",
        "is_generic": False,
    },
]


@pytest.mark.json_response(DRUG_DETAILS_TEST_JSON_DATA)
def test_query_drug_details(mock_query_api_json_response):
    api = OpenPrescribingHttpApi()
    response = api.query_drug_details()
    mock_query_api_json_response.assert_called_once()
    assert response == [DrugDetail.from_dict(o) for o in DRUG_DETAILS_TEST_JSON_DATA]


FEATURE_COLLECTION_TEST_JSON_DATA: FeatureCollection = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "ABCD:1234"}},
    "features": [
        {
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
    ],
}


@pytest.mark.json_response(FEATURE_COLLECTION_TEST_JSON_DATA)
def test_query_org_location(mock_query_api_json_response):
    api = OpenPrescribingHttpApi()
    actual = api.query_org_location()
    expected = CCGBoundaries(FEATURE_COLLECTION_TEST_JSON_DATA)
    mock_query_api_json_response.assert_called_once()
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


@pytest.mark.json_response(SPENDING_BY_CCG_TEST_JSON_DATA)
def test_http_api_data_provider_get_chemical_spending_for_ccg(mock_query_api_json_response):
    provider = HttpApiDataProvider()
    response = provider.chemical_spending_for_ccg(chemical="BADF00D", ccg="ABC")
    mock_query_api_json_response.assert_called_once_with(
        path="spending_by_ccg", api_params={"code": "BADF00D", "org": "ABC"}
    )
    assert response == [CCGSpend.from_dict(o) for o in SPENDING_BY_CCG_TEST_JSON_DATA]


@pytest.mark.json_response(DRUG_DETAILS_TEST_JSON_DATA)
def test_http_api_data_provider_get_drug_details(mock_query_api_json_response):
    provider = HttpApiDataProvider()
    response = provider.drug_details(query="lipid", exact=False)
    mock_query_api_json_response.assert_called_once_with(
        path="bnf_code", api_params={"q": "lipid", "exact": "false"}
    )
    assert response == [DrugDetail.from_dict(o) for o in DRUG_DETAILS_TEST_JSON_DATA]


@pytest.mark.json_response(FEATURE_COLLECTION_TEST_JSON_DATA)
def test_http_api_data_provider_get_ccg_boundaries(mock_query_api_json_response):
    provider = HttpApiDataProvider()
    provider.ccg_boundaries()
    mock_query_api_json_response.assert_called_once_with(
        path="org_location", api_params={"org_type": "ccg"}
    )
