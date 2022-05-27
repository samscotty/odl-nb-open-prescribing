import json
from os import path

import pytest


@pytest.fixture
def data_filename():
    def re(filename):
        return path.join(path.dirname(__file__), "data", filename)

    return re


@pytest.fixture
def boundaries_json(data_filename):
    with open(data_filename("boundaries.json"), "r") as f:
        return json.loads(f.read())


@pytest.fixture
def spend_json(data_filename):
    with open(data_filename("spend.json"), "r") as f:
        return json.load(f)
