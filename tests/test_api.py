from datetime import date

import pytest

from nb_open_prescribing.api import OpenPrescribingHttpApi
from nb_open_prescribing.model import CCGBoundaries, CCGSpend


@pytest.mark.usefixtures("mock_api_search_response")
@pytest.mark.parametrize(
    "response_fixture,expected",
    [
        (
            "spend_by_ccg",
            [
                CCGSpend(
                    items=10,
                    quantity=10_000,
                    actual_cost=1000.00,
                    date=date(2022, 1, 1),
                    row_id="fake",
                    row_name="fake",
                )
            ],
        ),
    ],
)
def test_query_spending_by_ccg(expected):
    api = OpenPrescribingHttpApi()
    assert api.query_spending_by_ccg() == expected


@pytest.mark.usefixtures("mock_api_search_response")
@pytest.mark.parametrize(
    "response_fixture,expected",
    [
        (
            "feature_collection",
            CCGBoundaries(
                {
                    "type": "FeatureCollection",
                    "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                    "features": [
                        {
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
                    ],
                }
            ),
        ),
    ],
)
def test_query_org_location(expected):
    api = OpenPrescribingHttpApi()
    boundaries = api.query_org_location()
    assert boundaries.features == expected.features
