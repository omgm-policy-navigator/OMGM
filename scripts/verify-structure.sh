#!/usr/bin/env sh
set -eu

test ! -d src
test -d backend/src/app
test -d backend/tests
test -d frontend/src
test -d backend/data/policy-seed
test -f backend/data/policy-seed/02_policy.csv
test -f backend/data/policy-seed/08_policy_document.csv
test -d infra/postgres/init
test -f compose.yaml
test -d docs
