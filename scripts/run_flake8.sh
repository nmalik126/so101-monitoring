#!/bin/bash

flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics \
    --extend-exclude=src/so101_monitoring/proto/
