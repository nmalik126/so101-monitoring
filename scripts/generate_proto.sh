#!/bin/bash

protoc \
    -I proto/so101-monitoring \
    --python_out=src/so101_monitoring/proto \
    --mypy_out=src/so101_monitoring/proto \
    proto/so101-monitoring/telemetry/telemetry.proto

