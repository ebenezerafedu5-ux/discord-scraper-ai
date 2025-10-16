#!/usr/bin/env bash
set -eux
pip install -r requirements.txt
npx playwright install --with-deps chromium
