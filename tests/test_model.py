from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from nb_open_prescribing.model import (
    BNFCode,
    Chemical,
    DrugDetail,
    Feature,
    FeatureCollection,
    LocationBoundaries,
    LocationSpend,
    Product,
    SpendingBySICBL,
)

SPEND_BY_CCG_TEST_DATA: SpendingBySICBL = {
    "items": 100,
    "quantity": 10000.0,
    "actual_cost": 12345.67,
    "date": "2022-01-01",
    "row_id": "ABC",
    "row_name": "ANOTHER CCG",
}


def test_spend_by_ccg_from_dict():
    assert LocationSpend.from_dict(SPEND_BY_CCG_TEST_DATA) == LocationSpend(
        items=100,
        quantity=10000.0,
        actual_cost=12345.67,
        date=date(2022, 1, 1),
        row_id="ABC",
        row_name="ANOTHER CCG",
    )


def test_spend_by_ccg_from_dict_parses_datetime():
    assert isinstance(LocationSpend.from_dict(SPEND_BY_CCG_TEST_DATA).date, date)


def test_spend_by_ccg_frostiness():
    with pytest.raises(FrozenInstanceError):
        LocationSpend.from_dict(SPEND_BY_CCG_TEST_DATA).items = 1_000


BNF_CODE_TEST_DATA: BNFCode = {
    "type": "BNF section",
    "id": "2.12",
    "name": "Lipid-regulating drugs",
}

BNF_CHEMICAL_TEST_DATA: Chemical = {
    "type": "chemical",
    "id": "021200000",
    "name": "Other Lipid-Regulating Preps",
    "section": "2.12: Lipid-regulating drugs",
}

BNF_PRODUCT_TEST_DATA: Product = {
    "type": "product",
    "id": "0212000F0AA",
    "name": "Colestyramine (Lipid lowering)",
    "is_generic": True,
}


@pytest.mark.parametrize(
    "data", [BNF_CODE_TEST_DATA, BNF_CHEMICAL_TEST_DATA, BNF_PRODUCT_TEST_DATA]
)
def test_drug_detail_from_dict(data):
    assert DrugDetail.from_dict(data) == DrugDetail(
        type=data["type"], id=data["id"], name=data["name"]
    )


@pytest.mark.parametrize(
    "data", [BNF_CODE_TEST_DATA, BNF_CHEMICAL_TEST_DATA, BNF_PRODUCT_TEST_DATA]
)
def test_drug_detail_frostiness(data):
    with pytest.raises(FrozenInstanceError):
        DrugDetail.from_dict(data).id = "ABC123"


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


def test_ccg_boundaries_get_crs_projection():
    assert (
        LocationBoundaries(FEATURE_COLLECTION_TEST_DATA).crs
        == FEATURE_COLLECTION_TEST_DATA["crs"]["properties"]["name"]
    )


def test_ccg_boundaries_list_features():
    assert LocationBoundaries(FEATURE_COLLECTION_TEST_DATA).features == [FEATURE_TEST_DATA]


def test_ccg_boundaries_get_feature():
    assert (
        LocationBoundaries(FEATURE_COLLECTION_TEST_DATA)["DEADBEEF"] == FEATURE_COLLECTION_TEST_DATA
    )


def test_ccg_boundaries_iterable():
    assert [f for f in (LocationBoundaries(FEATURE_COLLECTION_TEST_DATA))] == [FEATURE_TEST_DATA]
