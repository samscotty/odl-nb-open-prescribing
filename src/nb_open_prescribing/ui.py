from collections import ChainMap
from dataclasses import dataclass
from typing import Any, MutableMapping, Optional

import matplotlib.pyplot as plt
from ipyleaflet import GeoJSON, Map, basemaps
from ipywidgets import (
    HTML,
    Accordion,
    Button,
    Combobox,
    Dropdown,
    Label,
    Layout,
    Output,
    VBox,
)
from matplotlib.ticker import FuncFormatter

from .api import DataProvider, HttpApiDataProvider
from .model import CCGBoundaries, CCGSpend, DrugDetail, FeatureCollection
from .util import RateLimiter


class OpenPrescribingDataExplorer(VBox):

    """UI for exploring Open Prescribing CCG spend data.

    Args:
        data_provider: Provider for Open Prescribing data.
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(self, data_provider: Optional[DataProvider] = None, **kwargs):
        super().__init__(**kwargs)
        self.data_provider = data_provider if data_provider is not None else HttpApiDataProvider()
        # active search box selections
        self._drug_name_to_id_mapping: dict[str, str] = {}
        self._drug_code: Optional[str] = None

        # UI components
        self.title = HTML(
            "<h1>Search CCG Prescribing Data</h1>"
            "<p>Use the map to select a CCG and the search box to find a chemical/product.</p>"
        )
        self.map = CCGIPyLeafletMap(self.data_provider.ccg_boundaries())
        self.drug_selector = Combobox(
            ensure_option=False,
            placeholder="Add names or codes e.g. Cerazette",
            layout=Layout(width="100%"),
        )
        self.search_button = Button(
            description="Show me the data",
            button_style="info",
            layout=Layout(height="35px", margin="10px 1px"),
            disabled=True,
        )
        self.status_message = Label(layout=Layout(margin="0px 1px 10px"))
        self.spend_plotter = SpendPlotter()

        # event handlers
        self.drug_selector.observe(self._select_handler, "value")
        self.search_button.on_click(self._click_handler)

        # add components to the display
        self.children = [
            self.title,
            self.map,
            self.drug_selector,
            self.search_button,
            self.status_message,
            self.spend_plotter,
        ]

    @property
    def drug_code(self) -> Optional[str]:
        """Selected drug ID."""
        return self._drug_code

    @property
    def ccg_code(self) -> Optional[str]:
        """Selected CCG."""
        if self.map.selected_ccg is None:
            return None
        return self.map.selected_ccg.code

    def _search_spending(self, drug_code: str, ccg_code: str) -> list[CCGSpend]:
        """Request spending data for a given drug for a given CCG."""
        return self.data_provider.chemical_spending_for_ccg(chemical=drug_code, ccg=ccg_code)

    def _search_drugs(self, user_entered_input: str) -> list[DrugDetail]:
        """Request BNF sections, chemicals and presentations matching a given query.

        Note:
            A rate limiter decorator is applied to the method to prevent excessive requests
            to the API.

        """
        return self.data_provider.drug_details(query=user_entered_input)

    @RateLimiter()
    def _select_handler(self, change) -> None:
        """Handler for the drug selector UI.

        Args:
            change: The observed ipywidget change.

        """
        user_entered_input = str(change["new"])
        # remove current selection
        self._drug_code = None
        # require a minimum of 3 characters before displaying any results
        if len(user_entered_input.strip()) < 3:
            self.search_button.disabled = True
            self._drug_name_to_id_mapping = {}
        # if selection has been made, remove other options
        elif self.drug_selector.value in self.drug_selector.options:
            self.search_button.disabled = False
            self._drug_code = self._drug_name_to_id_mapping[self.drug_selector.value]
            self._drug_name_to_id_mapping = {}
        # otherwise query API for more possible matches
        else:
            self.search_button.disabled = True
            self._drug_name_to_id_mapping = {
                f"{o.type}: {o.name} ({o.id})": o.id
                for o in self._search_drugs(user_entered_input)
                if o.type in ("chemical", "product")
            }

        # update possible matches
        self.drug_selector.options = [o for o in self._drug_name_to_id_mapping.keys()]

    def _click_handler(self, _) -> None:
        """Handler for the search button UI."""
        # ensure both fields are set
        if (ccg_code := self.ccg_code) is None or (drug_code := self._drug_code) is None:
            self.status_message.value = (
                "Nothing to search for, please select a CCG and a product/chemical."
            )
            return None

        self.search_button.disabled = True
        self.status_message.value = "Fetching the data..."
        data = self._search_spending(drug_code, ccg_code)
        # display the data
        self.spend_plotter.data = data
        self.spend_plotter.set_title(f"{self.map.label.value} - {self.drug_selector.value}")
        self.status_message.value = f"Found {len(data)} results."
        self.search_button.disabled = False


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
    ) -> None:
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
        """Highlighted CCG layer."""
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
        layer = self._construct_geojson_layer(self.boundaries[code])
        self.selected_ccg = CCGIPyLeafletLayer(code, layer)

    def _construct_geojson_layer(self, feature_collection: FeatureCollection) -> GeoJSON:
        """Create a styled ipyleaflet Geo JSON layer."""
        return GeoJSON(
            data=feature_collection,
            style={
                "dashArray": "2",
                "opacity": 1,
                "fillColor": "white",
                "fillOpacity": 0.6,
                "weight": 1,
            },
        )

    def _click_handler(self, event=None, feature=None, properties=None) -> None:
        """Handler for the ipyleaflet layers."""
        name, code = (properties.get(k) for k in ("name", "code"))
        self.select_ccg(code)
        self.label.value = name


class SpendPlotter(VBox):

    """UI for plotting Open Prescribing CCG spend data.

    Args:
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data: list[CCGSpend] = []
        self._yvar_field_to_label_mapping = {
            "items": "Items",
            "quantity": "Quantity",
            "actual_cost": "Actual Cost (£)",
        }

        # define widgets
        self.faq = FAQ()
        self.yvar_selector = Dropdown(
            description="Y-Axis",
            options=[(v, k) for k, v in self._yvar_field_to_label_mapping.items()],
            layout=Layout(margin="15px 1px 10px"),
        )
        self.output = Output()

        # matplotlib figure/axis
        with self.output:
            # prevent duplicate render
            plt.ioff()
            self.fig, self.ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
            self.ax.set_xlabel("Date")
            plt.ion()
            plt.show()
        self.ax.grid(c="#eee")
        self.fig.canvas.toolbar_position = "bottom"

        # event handlers
        self.yvar_selector.observe(self._change_handler, "value")

        # do not display UI components on instantiation
        self.hide()

        self.children = [self.faq, self.yvar_selector, self.output]

    @property
    def data(self) -> list[CCGSpend]:
        """CCG spend data."""
        return list(self._data)

    @data.setter
    def data(self, new_data: list[CCGSpend]) -> None:
        if new_data:
            self.show(new_data)
        else:
            self.hide()
        self._data = list(new_data)

    def show(self, data: list[CCGSpend]) -> None:
        """Render the plot with new data and display the UI components.

        Args:
            data: CCG spend data.

        """
        x, y = zip(*((o.date, getattr(o, self.yvar_selector.value)) for o in data))
        with self.output:
            self.ax.clear()
            self.ax.plot(x, y, ".-")
        # prettify the tick labels
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        self.ax.set_ylabel(self._yvar_field_to_label_mapping[self.yvar_selector.value])
        self.ax.grid(c="#eee")
        self.layout.display = None

    def hide(self) -> None:
        """Hide the UI components."""
        self.layout.display = "none"

    def set_title(self, title: str) -> None:
        """Display a title on the current figure."""
        self.fig.canvas.manager.set_window_title(title)

    def _change_handler(self, _) -> None:
        """Handler for the dropdown selector."""
        self.show(self._data)


class FAQ(VBox):

    """Expandable UI box displaying a glossary of the prescribing dataset terms.

    Args:
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        faq = HTML(
            """
            <h2>What are prescription <i>Items</i>?</h2>
            <p>
                Items counts the number of times a medicine has been prescribed.
                It says nothing about how much of it has been prescribed (for that see quantity)
                as some presciptions will be for many weeks’ worth of treatment
                while others will be much smaller.
            </p>
            <h2>What does <i>Quantity</i> mean?</h2>
            <p>
                Quantity is the total amount of a medicine that has been prescribed,
                but the units used depend on the particular form the medicine is in:
                <ul>
                    <li>
                        Where the formulation is tablet, capsule, ampoule, vial etc
                        the quantity will be the number of tablets, capsules, ampoules, vials etc
                    </li>
                    <li>
                        Where the formulation is a liquid the quantity will bethe number of
                        millilitres
                    </li>
                    <li>
                        Where the formulation is a solid form (eg. cream, gel, ointment)
                        the quantity will be the number of grams
                    </li>
                    <li>
                        Where the formulation is inhalers the quantity is usually
                        the number of inhalers
                        (but there are occasionally inconsistencies here so exercise caution
                        when analysing this data)
                    </li>
                </ul>
            </p>
            <p>
                Care must be taken when adding together quantities.
                Obviously quantities cannot be added across units.
                But even within a given unit it may not make sense to add together quantities
                of different preparations with different strengths and formulations.
            </p>
            <h2>What is <i>Actual Cost</i>?</h2>
            <p>
                Actual cost is the estimated cost to the NHS of supplying a medicine.
                The Drug Tariff and other price lists specify a Net Ingredient Cost (NIC)
                for a drug, but pharmacists usually receive a discount on this price.
                Additionally they receive a "container allowance" each time they dispense
                a prescription. The actual cost is estimated from the net ingredient cost
                by subtracting the average percentage discount received by pharmacists
                in the previous month and adding in the cost of the container allowance.
            </p>
            </br>
            """
        )
        accordion = Accordion([faq], selected_index=None)
        accordion.set_title(0, "FAQ")

        self.children = [accordion]
