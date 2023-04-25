# Open Prescribing Data Explorer

Python modules for exploring England's prescribing data in a Jupyter Notebook.


## Description

Uses the [OpenPrescribing.net](https://openprescribing.net) RESTful API, created by the Bennett Institute for Applied Data Science, for exploring anonymised data about drugs prescribed by GPs, published by the NHS in England.


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
