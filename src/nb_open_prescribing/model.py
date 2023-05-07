from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Literal, Optional, TypedDict, Union


class SpendingBySICBL(TypedDict):
    items: int
    quantity: float
    actual_cost: float
    date: str
    row_id: str
    row_name: str


@dataclass(frozen=True)
class LocationSpend:
    items: int
    quantity: float
    actual_cost: float
    date: date
    row_id: str
    row_name: str

    @classmethod
    def from_dict(cls, data: SpendingBySICBL):
        return cls(
            items=data["items"],
            quantity=data["quantity"],
            actual_cost=data["actual_cost"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            row_id=data["row_id"],
            row_name=data["row_name"],
        )


BnfCodeType = Literal[
    "BNF chapter", "BNF section", "BNF paragraph", "chemical", "product", "product format"
]


class BNFCode(TypedDict):
    type: BnfCodeType
    id: str
    name: str


class Chemical(BNFCode):
    section: str


class Product(BNFCode):
    is_generic: bool


# possible API responses from BNF search
BnfCodeOrName = Union[BNFCode, Chemical, Product]


@dataclass(frozen=True)
class DrugDetail:
    type: BnfCodeType
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: BnfCodeOrName):
        return cls(type=data["type"], id=data["id"], name=data["name"])


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


class LocationBoundaries:

    """Boundaries of all Sub-ICB Locations.

    Args:
        feature_collection: A GeoJSON object with the type `FeatureCollection`.

    """

    def __init__(self, feature_collection: FeatureCollection):
        self.feature_collection = deepcopy(feature_collection)
        # used to construct a new Feature Collection for a specific CCG
        self._code_to_feature_mapping = {
            feature["properties"]["code"]: feature for feature in feature_collection["features"]
        }

    @property
    def crs(self) -> str:
        """Coordinate Reference System."""
        return self.feature_collection["crs"]["properties"]["name"]

    @property
    def features(self) -> list[Feature]:
        """List the Features in the FeatureCollection."""
        return list(self._code_to_feature_mapping.values())

    def feature_collection_from_code(self, code: str) -> FeatureCollection:
        """Construct a new FeatureCollection for a given Sub-ICB Location.

        Args:
            code: Location code.

        """
        return FeatureCollection(
            type=self.feature_collection["type"],
            crs=self.feature_collection["crs"],
            features=[self._code_to_feature_mapping[code]],
        )

    def __getitem__(self, code: str) -> FeatureCollection:
        return self.feature_collection_from_code(code)

    def __iter__(self) -> Iterable[Feature]:
        return (feature for feature in self.features)
