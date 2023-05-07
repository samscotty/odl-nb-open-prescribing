import logging
from abc import abstractmethod
from collections import ChainMap
from typing import Final, MutableMapping, Optional, Protocol
from urllib.parse import urljoin

from requests import Response, Session

from .model import DrugDetail, LocationBoundaries, LocationSpend

_SERVICE_BASE_URL: Final[str] = "https://openprescribing.net"

ApiParams = MutableMapping[str, str]


class OpenPrescribingHttpApi:

    """Interface for Open Prescribing RESTful API service.

    Args:
        headers: Dictionary of HTTP headers to send with requests.

    """

    def __init__(self, headers: Optional[MutableMapping[str, str]] = None) -> None:
        self._api_version = 1.0
        self._service_url = f"{_SERVICE_BASE_URL}/api/{self._api_version}/"
        self._session = Session()
        if headers is not None:
            self._session.headers.update(headers)
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"connected to {self._service_url}")

    def query_org_location(self, api_params: Optional[ApiParams] = None) -> LocationBoundaries:
        """Search for the boundaries of a Sub-ICB Location, or location of a practice, by code.

        Args:
            api_params: Query parameters to send with GET request.

        Note:
            API returns GeoJSON.

        Returns:
            Location boundaries.

        """
        response = self._search(path="org_location", api_params=api_params)
        return LocationBoundaries(response.json())

    def query_spending_by_location(
        self, api_params: Optional[ApiParams] = None
    ) -> list[LocationSpend]:
        """Queries the last five years of data and returns spending and items by Sub-ICB Location by month.

        Args:
            api_params: Query parameters to send with GET request.

        Returns:
            Monthly spending and items for each Sub-ICB Location.

        """
        response = self._search(path="spending_by_sicbl", api_params=api_params)
        return [LocationSpend.from_dict(x) for x in response.json()]

    def query_spending_by_code(self, api_params: Optional[ApiParams] = None):
        """Queries the last five years of data and returns total spending and items by month."""
        # return self._search(path="spending", api_params=api_params)
        raise NotImplementedError

    def query_drug_details(self, api_params: Optional[ApiParams] = None) -> list[DrugDetail]:
        """Queries the official name and code of BNF sections, chemicals and presentations."""
        response = self._search(path="bnf_code", api_params=api_params)
        return [DrugDetail.from_dict(x) for x in response.json()]

    def _search(self, path: str, api_params: Optional[ApiParams] = None, **kwargs) -> Response:
        """Perform GET request.

        Args:
            path: API path.
            api_params: Query parameters.
            **kwargs: Keyword arguments compatible to GET request function.

        Returns:
            API response from HTTP GET request.

        Raises:
            HttpError: if one occurred.

        """
        # ensure response is always JSON formatted
        params = ChainMap({"format": "json"})
        if api_params:
            params.maps.append(api_params)
        api_url = urljoin(self._service_url, path)
        self.logger.debug(f"request GET: {api_url} query_params: {api_params}")
        response = self._session.get(api_url, params=params, **kwargs)
        response.raise_for_status()
        return response


class DataProvider(Protocol):

    """Protocol class for prescribing data providers.

    Note:
        Enables structural subtyping during typechecking.

    """

    @abstractmethod
    def location_boundaries(self) -> LocationBoundaries:
        """Get the boundaries of all Sub-ICB Locations.

        Returns:
            Location boundaries.

        """
        ...

    @abstractmethod
    def chemical_spending_for_location(self, chemical: str, location: str) -> list[LocationSpend]:
        """Prescription spending data for a chemical in a specified location.

        Args:
            chemical: Chemical code.
            location: ODS code.

        Returns:
            Chemical prescription spending for location.

        """
        ...

    @abstractmethod
    def drug_details(self, query: str, exact: bool = ...) -> list[DrugDetail]:
        """All BNF sections, chemicals and presentations matching a name (case-insensitive)
         or a code.

        Args:
            query: Query string.
            exact: Exactly match a name or code.

        Returns:
            Official name and code of matching BNF sections, chemicals and presentations.

        """
        ...


class HttpApiDataProvider(DataProvider):

    """Data provider for the Open Prescribing RESTful API.

    Args:
        api: Open Prescribing RESTful API interface.

    """

    def __init__(self, api: Optional[OpenPrescribingHttpApi] = None) -> None:
        self._api = api if api is not None else OpenPrescribingHttpApi()

    def location_boundaries(self) -> LocationBoundaries:
        """Get the boundaries of all Sub-ICB Locations.

        Returns:
            Location boundaries.

        """
        # NOTE: API parameter uses a former geographical area identifier (CCG)
        return self._api.query_org_location(api_params={"org_type": "ccg"})

    def chemical_spending_for_location(self, chemical: str, location: str) -> list[LocationSpend]:
        """Prescription spending data for a chemical in a specified Sub-ICB Location.

        Args:
            chemical: Chemical code.
            location: ODS code.

        Returns:
            Chemical prescription spending for Sub-ICB Location.

        """
        return self._api.query_spending_by_location(api_params={"code": chemical, "org": location})

    def drug_details(self, query: str, exact: bool = False) -> list[DrugDetail]:
        """All BNF sections, chemicals and presentations matching a name (case-insensitive)
        or a code.

        Args:
            query: Query string.
            exact: Exactly match a name or code.

        Returns:
            Official name and code of matching BNF sections, chemicals and presentations.

        """
        return self._api.query_drug_details(
            api_params={"q": query, "exact": "true" if exact else "false"}
        )
