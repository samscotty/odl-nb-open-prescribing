from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional, TypedDict


class SpendByCCG(TypedDict):
    items: int
    quantity: float
    actual_cost: float
    date: str
    row_id: str
    row_name: str


class FeatureProperties(TypedDict):
    name: str
    code: str
    ons_code: Optional[str]
    org_type: str


Coordinates = list[list[list[float]]]


class Geometry(TypedDict):
    type: str
    coordinates: Coordinates


class Feature(TypedDict):
    type: str
    properties: FeatureProperties
    geometry: Geometry


class CRSProperties(TypedDict):
    name: str


class CRS(TypedDict):
    type: str
    properties: CRSProperties


class FeatureCollection(TypedDict):
    type: str
    crs: CRS
    features: list[Feature]


@dataclass(frozen=True)
class CCGSpend:
    items: int
    quantity: float
    actual_cost: float
    date: date
    row_id: str
    row_name: str

    @classmethod
    def from_dict(cls, data: SpendByCCG):
        return cls(
            items=data["items"],
            quantity=data["quantity"],
            actual_cost=data["actual_cost"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            row_id=data["row_id"],
            row_name=data["row_id"],
        )


class CCGBoundaries:
    def __init__(self, features: FeatureCollection):
        self._code_to_feature_mapping = {
            feature["properties"]["code"]: feature for feature in features["features"]
        }

    @property
    def features(self) -> list[Feature]:
        return list(self._code_to_feature_mapping.values())

    def __getitem__(self, code: str) -> Feature:
        return self._code_to_feature_mapping[code]

    def __iter__(self) -> Iterable[Feature]:
        return (feature for feature in self.features)
