# Open Prescribing CCG Data Explorer

Python modules for CCG data explorer in Jupyter Notebooks.


## Description

ipyleaflet widget for exploring CCG data in Jupyter Notebooks.


## Setup for Development

Install Poetry via:

```sh
curl -sSL https://install.python-poetry.org | python3 -
```

Install all required packages:

```sh
poetry install
```

After this you're good to go. To run pytest or similar tools that were installed by Poetry there
are two options:

```sh
# Either prepend every time...
poetry run pytest
poetry run black src tests

# ... or drop into a sub-shell for longer sessions.
poetry shell
pytest
black src tests
```

To run CI actions run the dedicated scripts:

```sh
poetry run scripts/style.sh
poetry run scripts/test.sh
```
