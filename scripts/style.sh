#!/bin/sh
set -eux
target_list="src tests"

isort --check --diff ${target_list} || exit
black --check --diff ${target_list} || exit
flake8 ${target_list} || exit
mypy --no-error-summary ${target_list} || exit