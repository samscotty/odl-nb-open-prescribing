from collections import ChainMap
from dataclasses import dataclass
from typing import Any, MutableMapping, Optional

from ipyleaflet import GeoJSON, Map, basemaps
from ipywidgets import Label, VBox

from .api import DataProvider, HttpApiDataProvider
from .model import CCGBoundaries


class OpenPrescribingDataExplorer(VBox):

    """ """

    def __init__(self, data_provider: Optional[DataProvider] = None, **kwargs):
        super().__init__(**kwargs)
        self.data_provider = data_provider if data_provider is not None else HttpApiDataProvider()

        # UI components
        self.map = CCGIPyLeafletMap(self.data_provider.ccg_boundaries())

        # add components to the display
        self.children = [self.map]


@dataclass
class CCGIPyLeafletLayer:

    """CCG created from a GeoJSON data structure."""

    code: str
    layer: GeoJSON


class CCGIPyLeafletMap(VBox):

    """ipyleaflet Map interface for CCG boundary data.

    Args:
        boundaries: CCG feature collection.
        map_attrs: ipyleaflet map attributes.
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(
        self,
        boundaries: CCGBoundaries,
        map_attrs: Optional[MutableMapping[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.boundaries = boundaries
        self.ccgs = GeoJSON(
            data=self.boundaries.feature_collection,
            style={"opacity": 1, "fillOpacity": 0.1, "weight": 0},
            hover_style={"fillColor": "white", "fillOpacity": 0.5},
        )
        self._selected_ccg: Optional[CCGIPyLeafletLayer] = None

        # UI components
        self.ipyleaflet_map = Map(
            # ensure certain attributes are used
            # and provide appropriate defaults for any left unspecified
            **ChainMap(
                {
                    "basemap": basemaps.CartoDB.Positron,
                    # NOTE ipyleaflet CRS EPSG:4326 issue
                    # "crs": projections.get(self.boundaries.crs, projections.EPSG4326),
                    "fit_bounds": [[49, -7], [57, 7]],
                },
                map_attrs if map_attrs is not None else {},
                {
                    "center": (52.9, -2),
                    "double_click_zoom": False,
                    "max_zoom": 9,
                    "min_zoom": 6,
                    "scroll_wheel_zoom": True,
                    "zoom": 6,
                    "zoom_snap": 0.5,
                },
            )
        )
        # display selected CCG
        self.label = Label()

        # add base CCG boundaries to the map
        self.ipyleaflet_map.add_layer(self.ccgs)

        # event handlers
        self.ccgs.on_click(self._click_handler)

        # display UI
        self.children = [self.ipyleaflet_map, self.label]

    @property
    def selected_ccg(self) -> Optional[CCGIPyLeafletLayer]:
        """The currently highlighted CCG layer."""
        return self._selected_ccg

    @selected_ccg.setter
    def selected_ccg(self, ccg: CCGIPyLeafletLayer) -> None:
        if self._selected_ccg is not None:
            self.ipyleaflet_map.remove_layer(self._selected_ccg.layer)

        self._selected_ccg = ccg
        self.ipyleaflet_map.add_layer(self._selected_ccg.layer)

    def select_ccg(self, code: str) -> None:
        """Highlight a CCG on the map.

        Args:
            code: CCG code.

        """
        layer = GeoJSON(
            data=self.boundaries[code],
            style={
                "dashArray": "2",
                "opacity": 1,
                "fillColor": "white",
                "fillOpacity": 0.6,
                "weight": 1,
            },
        )
        self.selected_ccg = CCGIPyLeafletLayer(code, layer)

    def _click_handler(self, event=None, feature=None, properties=None) -> None:
        name, code = (properties.get(k) for k in ("name", "code"))
        self.select_ccg(code)
        self.label.value = name
