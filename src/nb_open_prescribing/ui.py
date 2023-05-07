from collections import ChainMap
from dataclasses import dataclass
from typing import Any, MutableMapping, Optional

import matplotlib.pyplot as plt
from ipyleaflet import GeoJSON, Map, basemaps
from ipywidgets import (
    HTML,
    Accordion,
    Button,
    Dropdown,
    Label,
    Layout,
    Output,
    Select,
    Text,
    VBox,
)
from matplotlib.ticker import FuncFormatter

from .api import DataProvider, HttpApiDataProvider
from .model import FeatureCollection, LocationBoundaries, LocationSpend
from .util import RateLimiter


class OpenPrescribingDataExplorer(VBox):

    """UI for exploring England's prescribing data.

    Args:
        data_provider: Provider for Open Prescribing data.
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(self, data_provider: Optional[DataProvider] = None, **kwargs):
        super().__init__(**kwargs)
        self.data_provider = data_provider if data_provider is not None else HttpApiDataProvider()

        # UI components
        self.title = HTML(
            "<h1>Search GP Prescribing Data</h1>"
            "<p>Use the map to select a location and the search box to find a chemical/product.</p>"
        )
        self.map = LocationBoundariesMap(parent=self)
        self.drug_selector = DrugSearchBox(parent=self)
        self.search_button = Button(
            description="Show me the data",
            button_style="info",
            layout=Layout(height="35px", margin="10px 1px"),
            disabled=True,
        )
        self.status_message = Label(layout=Layout(margin="0px 1px 10px"))
        self.spend_plotter = SpendPlotter()

        # event handlers
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

    def is_submittable(self) -> bool:
        if self.map.get_location_code() and self.drug_selector.get_selected_drug_id():
            self.search_button.disabled = False
            return True
        else:
            self.search_button.disabled = True
            return False

    def _click_handler(self, _) -> None:
        """Handler for the search button UI."""
        location_code = self.map.get_location_code()
        drug_code = self.drug_selector.get_selected_drug_id()
        # ensure both fields are set
        if not (location_code or drug_code):
            self.status_message.value = (
                "Nothing to search for, please select a location and a product/chemical."
            )
            return None

        self.search_button.disabled = True
        self.status_message.value = "Fetching the data..."
        data = self.data_provider.chemical_spending_for_location(
            chemical=drug_code, location=location_code
        )
        # display the data
        self.spend_plotter.data = data
        self.spend_plotter.set_title(f"{self.map.label.value} - {drug_code}")
        self.status_message.value = f"Found {len(data)} results."
        self.search_button.disabled = False


@dataclass
class LocationBoundariesLayer:

    """Location created from a GeoJSON data structure."""

    code: str
    layer: GeoJSON


class LocationBoundariesMap(VBox):

    """ipyleaflet Map interface for location boundary data.

    Args:
        parent: Open Prescribing Data Explorer.
        map_attrs: ipyleaflet map attributes.
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(
        self,
        parent: OpenPrescribingDataExplorer,
        map_attrs: Optional[MutableMapping[str, Any]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.parent = parent
        self.boundaries: LocationBoundaries = parent.data_provider.location_boundaries()
        self._geojson_layer = GeoJSON(
            data=self.boundaries.feature_collection,
            style={"opacity": 1, "fillOpacity": 0.1, "weight": 0},
            hover_style={"fillColor": "white", "fillOpacity": 0.5},
        )
        self._selected_layer: Optional[LocationBoundariesLayer] = None

        # UI components
        self.ipyleaflet_map = Map(
            # Ensure certain attributes are used
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
        # Display the selected location name
        self.label = Label()

        # Add the base location boundaries to the map
        self.ipyleaflet_map.add_layer(self._geojson_layer)

        # Event handlers
        self._geojson_layer.on_click(self._click_handler)

        # Display UI
        self.children = [self.ipyleaflet_map, self.label]

    @property
    def selected_layer(self) -> Optional[LocationBoundariesLayer]:
        """Highlighted location boundary layer."""
        return self._selected_layer

    @selected_layer.setter
    def selected_layer(self, layer: LocationBoundariesLayer) -> None:
        if self._selected_layer is not None:
            self.ipyleaflet_map.remove_layer(self._selected_layer.layer)

        self._selected_layer = layer
        self.ipyleaflet_map.add_layer(self._selected_layer.layer)

    def get_location_code(self) -> str:
        """Get the code of currently selected location.

        Note:
            Returns an empty string if no location is selected.

        Returns:
            The selected location code.

        """
        if (location := self.selected_layer) is None:
            return ""
        return location.code

    def select_location(self, code: str) -> None:
        """Highlight a location on the map.

        Args:
            code: ODS code.

        """
        layer = self._construct_geojson_layer(self.boundaries[code])
        self.selected_layer = LocationBoundariesLayer(code, layer)

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
        self.select_location(code)
        self.label.value = name
        self.parent.is_submittable()


class SpendPlotter(VBox):

    """UI for plotting Open Prescribing spend data.

    Args:
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data: list[LocationSpend] = []
        self._yvar_field_to_label_mapping = {
            "items": "Items",
            "quantity": "Quantity",
            "actual_cost": "Actual Cost (£)",
        }

        # Define widgets
        self.faq = FAQ()
        self.yvar_selector = Dropdown(
            description="Y-Axis",
            options=[(v, k) for k, v in self._yvar_field_to_label_mapping.items()],
            layout=Layout(margin="15px 1px 10px"),
        )
        self.output = Output()

        # Matplotlib figure/axis
        with self.output:
            # prevent duplicate render
            plt.ioff()
            self.fig, self.ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
            self.ax.set_xlabel("Date")
            plt.ion()
            plt.show()
        self.ax.grid(c="#eee")
        self.fig.canvas.toolbar_position = "bottom"

        # Event handlers
        self.yvar_selector.observe(self._change_handler, "value")

        # Do not display UI components on instantiation
        self.hide()

        self.children = [self.faq, self.yvar_selector, self.output]

    @property
    def data(self) -> list[LocationSpend]:
        """Location spend data."""
        return list(self._data)

    @data.setter
    def data(self, new_data: list[LocationSpend]) -> None:
        if new_data:
            self.show(new_data)
        else:
            self.hide()
        self._data = list(new_data)

    def show(self, data: list[LocationSpend]) -> None:
        """Render the plot with new data and display the UI components.

        Args:
            data: Location spend data.

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


class DrugSearchBox(VBox):

    """Combined text and dropdown UI component for searching the official name and code of
    BNF sections, chemicals and presentations.

    Args:
        **kwargs: Keyword arguments to pass to the ipywidget container.

    """

    def __init__(self, parent: OpenPrescribingDataExplorer, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        # Text box contains a valid code
        self._valid: bool = False

        self.text = Text(
            placeholder="Add names or codes e.g. Cerazette",
            layout=Layout(margin="2px 2px 0px 1px"),
        )
        self.dropdown = Select(layout=Layout(margin="-1px 2px 2px 1px"))

        # Event handlers
        self.text.observe(self._change_handler, names="value")
        self.dropdown.observe(self._select_handler, names="value")

        # Hide on instantiation
        self._show_dropdown(False)

    def get_selected_drug_id(self) -> str:
        """Get the ID of the currently selected drug.

        Note:
            Returns an empty string if no ID is selected.

        Returns:
            The selected drug ID.

        """
        if not self.is_valid():
            return ""
        return str(self.text.value)

    def is_valid(self) -> bool:
        """Check if the search box contains a valid drug ID.

        Returns:
            True if a valid ID is selected.

        """
        return self._valid

    def _set_options(self, options: list[tuple[str, str]]) -> None:
        """Set the dropdown options."""
        self.dropdown.unobserve(self._select_handler, names="value")
        self.dropdown.options = list(options)
        self.dropdown.value = None
        self.dropdown.observe(self._select_handler, names="value")

    def _show_dropdown(self, visible: bool) -> None:
        """Set the visibility of the dropdown."""
        if visible:
            self.children = [self.text, self.dropdown]
        else:
            self.dropdown.value = None
            self.children = [self.text]

    @RateLimiter()
    def _change_handler(self, change) -> None:
        """Handler for edits on the text field.

        The dropdown is adjusted to only include matching entries.

        Note:
            A rate limiter decorator is applied to the method to prevent excessive requests
            to the API.

        Args:
            change: The observed ipywidget change.

        """
        # Any change reset validity
        self._valid = False

        user_entered_input = str(change["new"])
        # Hide dropdown if fewer than 3 characters or a selection has been made
        if len(user_entered_input.strip()) < 3 or user_entered_input in self.dropdown.options:
            self._show_dropdown(False)
            return None

        new_options = [
            (f"{o.type}: {o.name} ({o.id})", o.id)
            for o in self.parent.data_provider.drug_details(query=user_entered_input)
            if o.type in ("chemical", "product")
        ]
        # Show the dropdown
        self._set_options(new_options)
        self._show_dropdown(True)

    def _select_handler(self, change) -> None:
        """Handler for selecting an item in the dropdown."""
        if not (selected_item := change["new"]):
            # Don't do anything on empty entries
            return None
        self.text.value = selected_item
        # A valid ID has been selected
        self._valid = True
        self._show_dropdown(False)
        self.parent.is_submittable()
