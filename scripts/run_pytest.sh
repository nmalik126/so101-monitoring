#!/bin/bash

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v -p pytest_cov --cov
