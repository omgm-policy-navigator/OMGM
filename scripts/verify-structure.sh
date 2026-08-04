#!/usr/bin/env sh
set -eu

test ! -d src
test -d backend/src/app
test -d backend/tests
test -d frontend/src
test -d data-pipeline/src/policy_pipeline
test -d infra/postgres/init
test -f compose.yaml
test -d docs
