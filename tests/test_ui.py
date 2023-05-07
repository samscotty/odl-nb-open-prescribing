from datetime import date
from functools import wraps
from warnings import catch_warnings, filterwarnings

import pytest
from ipyleaflet import GeoJSON
from matplotlib import use

from nb_open_prescribing.model import DrugDetail, LocationBoundaries, LocationSpend
from nb_open_prescribing.ui import (
    FAQ,
    CCGIPyLeafletLayer,
    CCGIPyLeafletMap,
    DrugSearchBox,
    OpenPrescribingDataExplorer,
    SpendPlotter,
)


def test_faq_displays_html():
    faq = FAQ()
    assert "<h2>What are prescription <i>Items</i>?</h2>" in str(faq.children)
    assert "<h2>What does <i>Quantity</i> mean?</h2>" in str(faq.children)
    assert "<h2>What is <i>Actual Cost</i>?</h2>" in str(faq.children)


def suppress_matplotlib_show(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with catch_warnings():
            filterwarnings(
                action="ignore",
                message="Matplotlib is currently using agg",
                category=UserWarning,
            )
            use("agg")
            return func(*args, **kwargs)

    return wrapper


CCG_SPEND_TEST_DATA = [
    LocationSpend(
        items=100,
        quantity=1000,
        actual_cost=50,
        date=date(2022, 1, 1),
        row_id="ABC",
        row_name="MORE CCGs",
    )
]


@suppress_matplotlib_show
def test_spend_plotter_data_setter():
    spend_plotter = SpendPlotter()
    spend_plotter.data = CCG_SPEND_TEST_DATA
    assert spend_plotter.data == CCG_SPEND_TEST_DATA
    assert spend_plotter._data == CCG_SPEND_TEST_DATA


@suppress_matplotlib_show
def test_spend_plotter_assign_new_data_shows_plot():
    spend_plotter = SpendPlotter()
    spend_plotter.data = CCG_SPEND_TEST_DATA
    assert spend_plotter.layout.display is None


@suppress_matplotlib_show
def test_spend_plotter_assign_no_data_hides_plot():
    spend_plotter = SpendPlotter()
    spend_plotter.data = []
    assert spend_plotter.layout.display == "none"


CCG_TEST_CODE = "DEADBEEF"

CCG_BOUNDARIES_TEST_DATA = LocationBoundaries(
    {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "ABCD:1234"}},
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "NICE PLACE",
                    "code": CCG_TEST_CODE,
                    "ons_code": None,
                    "org_type": "ABC",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-0.495026, 52.640236],
                            [-0.517397, 52.642379],
                            [-0.540261, 52.625966],
                            [-0.552939, 52.601349],
                            [-0.544174, 52.592888],
                            [-0.558118, 52.594484],
                            [-0.571904, 52.585803],
                            [-0.581547, 52.595868],
                            [-0.586973, 52.587429],
                            [-0.603019, 52.588591],
                        ]
                    ],
                },
            }
        ],
    }
)


GEO_JSON_LAYER = GeoJSON(
    data=CCG_BOUNDARIES_TEST_DATA[CCG_TEST_CODE],
    style={
        "dashArray": "2",
        "opacity": 1,
        "fillColor": "white",
        "fillOpacity": 0.6,
        "weight": 1,
    },
)


class MockDataProvider:
    def ccg_boundaries(self):
        return CCG_BOUNDARIES_TEST_DATA

    def chemical_spending_for_ccg(self, chemical, ccg):
        return CCG_SPEND_TEST_DATA

    def drug_details(self, query, exact=False):
        return DRUG_DETAILS_TEST_DATA


class MockOpenPrescribingDataExplorer:
    def __init__(self):
        self.data_provider = MockDataProvider()

    def is_submittable(self):
        return True


def test_ccg_ipyleaflet_map__construct_geojson_layer_instance():
    ccg_map = CCGIPyLeafletMap(MockOpenPrescribingDataExplorer())
    assert isinstance(
        ccg_map._construct_geojson_layer(CCG_BOUNDARIES_TEST_DATA[CCG_TEST_CODE]), GeoJSON
    )


@pytest.fixture
def mock_geojson_layer(mocker):
    def mock__construct_geojson_layer(self, feature_collection):
        return GEO_JSON_LAYER

    yield mocker.patch(
        "nb_open_prescribing.ui.CCGIPyLeafletMap._construct_geojson_layer",
        mock__construct_geojson_layer,
    )


def test_ccg_ipyleaflet_map_select_ccg_adds_layer(mock_geojson_layer):
    ccg_map = CCGIPyLeafletMap(MockOpenPrescribingDataExplorer())
    ccg_map.select_ccg(CCG_TEST_CODE)
    assert ccg_map.selected_ccg == CCGIPyLeafletLayer(code=CCG_TEST_CODE, layer=GEO_JSON_LAYER)
    assert ccg_map._selected_ccg == CCGIPyLeafletLayer(code=CCG_TEST_CODE, layer=GEO_JSON_LAYER)
    assert GEO_JSON_LAYER in ccg_map.ipyleaflet_map.layers


def test_ccg_ipyleaflet_map_selected_ccg_setter_removes_previous_layer():
    ccg_map = CCGIPyLeafletMap(MockOpenPrescribingDataExplorer())
    ccg_map.selected_ccg = CCGIPyLeafletLayer(code=CCG_TEST_CODE, layer=GEO_JSON_LAYER)
    new_layer = GeoJSON()
    ccg_map.selected_ccg = CCGIPyLeafletLayer(code="ANOTHERONE", layer=new_layer)
    assert GEO_JSON_LAYER not in ccg_map.ipyleaflet_map.layers
    assert new_layer in ccg_map.ipyleaflet_map.layers


def test_ccg_ipyleaflet_map_get_ccg_code():
    ccg_map = CCGIPyLeafletMap(MockOpenPrescribingDataExplorer())
    assert not ccg_map.get_ccg_code()
    ccg_map.select_ccg(CCG_TEST_CODE)
    assert ccg_map.get_ccg_code() == CCG_TEST_CODE


DRUG_DETAILS_TEST_DATA = [
    DrugDetail(type="chemical", id="ABC123", name="chemical"),
]


def test_drug_searchbox_get_selected_drug_id():
    search = DrugSearchBox(parent=MockOpenPrescribingDataExplorer())
    assert not search.get_selected_drug_id()
    # ensure the options are populated
    search.text.value = "ABC123"
    # simulate selecting an item in the dropdown
    search.dropdown.value = "ABC123"
    assert search.get_selected_drug_id() == "ABC123"


@pytest.fixture
def undecorated_select_handler(mocker):
    yield mocker.patch(
        "nb_open_prescribing.ui.DrugSearchBox._change_handler",
        DrugSearchBox._change_handler.__wrapped__,
    )


@suppress_matplotlib_show
@pytest.mark.parametrize(
    argnames=["user_entered_input", "has_results"],
    argvalues=[("A", False), ("AB", False), ("ABC", True)],
)
def test_open_prescribing_data_explorer__select_handler_requires_3_characters(
    user_entered_input, has_results, undecorated_select_handler
):
    op = OpenPrescribingDataExplorer(MockDataProvider())
    op.drug_selector.text.value = user_entered_input
    assert (len(op.drug_selector.dropdown.options) > 0) is has_results


@suppress_matplotlib_show
def test_open_prescribing_data_click_search_button():
    op = OpenPrescribingDataExplorer(MockDataProvider())
    op.search_button.click()
    assert "Nothing to search for" in op.status_message.value
