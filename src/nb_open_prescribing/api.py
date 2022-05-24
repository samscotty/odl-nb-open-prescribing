import logging
from collections import ChainMap
from typing import MutableMapping, Optional
from urllib.parse import urljoin

from requests import Response, Session

from .model import CCGBoundaries, CCGSpend

_SERVICE_BASE_URL = "https://openprescribing.net"

ApiParams = Optional[MutableMapping[str, str]]


class OpenPrescribingHttpApi:

    """ """

    def __init__(self, headers: Optional[MutableMapping[str, str]] = None) -> None:
        self._api_version = 1.0
        self._service_url = f"{_SERVICE_BASE_URL}/api/{self._api_version}/"
        self._session = Session()
        if headers is not None:
            self._session.headers.update(headers)
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"connected to {self._service_url}")

    def query_org_location(self, api_params: ApiParams = None) -> CCGBoundaries:
        """Search for the boundaries of a CCG, or location of a practice, by code.

        Note:
            API returns GeoJSON.

        """
        response = self._search(path="org_location", api_params=api_params)
        return CCGBoundaries(response.json())

    def query_spending_by_ccg(self, api_params: ApiParams = None) -> list[CCGSpend]:
        """Queries the last five years of data and returns spending and items by CCG by month."""
        response = self._search(path="spending_by_ccg", api_params=api_params)
        return [CCGSpend.from_dict(x) for x in response.json()]

    def query_spending_by_code(self, api_params: ApiParams = None):
        """Queries the last five years of data and returns total spending and items by month."""
        # return self._search(path="spending", api_params=api_params)
        raise NotImplementedError

    def _search(self, path: str, api_params: ApiParams = None, **kwargs) -> Response:
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
