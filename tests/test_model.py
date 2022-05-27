from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from nb_open_prescribing.model import (
    CCGBoundaries,
    CCGSpend,
    Feature,
    FeatureCollection,
    SpendByCCG,
)

SPEND_BY_CCG_TEST_DATA: SpendByCCG = {
    "items": 100,
    "quantity": 10000.0,
    "actual_cost": 12345.67,
    "date": "2022-01-01",
    "row_id": "ABC",
    "row_name": "ANOTHER CCG",
}


def test_spend_by_ccg_from_dict():
    assert CCGSpend.from_dict(SPEND_BY_CCG_TEST_DATA) == CCGSpend(
        items=100,
        quantity=10000.0,
        actual_cost=12345.67,
        date=date(2022, 1, 1),
        row_id="ABC",
        row_name="ANOTHER CCG",
    )


def test_spend_by_ccg_from_dict_parses_datetime():
    assert isinstance(CCGSpend.from_dict(SPEND_BY_CCG_TEST_DATA).date, date)


def test_spend_by_ccg_frostiness():
    with pytest.raises(FrozenInstanceError):
        CCGSpend.from_dict(SPEND_BY_CCG_TEST_DATA).items = 1_000


FEATURE_TEST_DATA: Feature = {
    "type": "Feature",
    "properties": {
        "name": "WHAT A FEATURE",
        "code": "DEADBEEF",
        "ons_code": None,
        "org_type": "ABC",
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-10.123456, 100.000000],
            ]
        ],
    },
}

FEATURE_COLLECTION_TEST_DATA: FeatureCollection = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "ABCD:1234"}},
    "features": [FEATURE_TEST_DATA],
}


def test_ccg_boundaries_list_features():
    assert CCGBoundaries(FEATURE_COLLECTION_TEST_DATA).features == [FEATURE_TEST_DATA]


def test_ccg_boundaries_get_feature():
    assert CCGBoundaries(FEATURE_COLLECTION_TEST_DATA)["DEADBEEF"] == FEATURE_TEST_DATA


def test_ccg_boundaries_iterable():
    assert [f for f in (CCGBoundaries(FEATURE_COLLECTION_TEST_DATA))] == [FEATURE_TEST_DATA]
