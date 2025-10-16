#!/usr/bin/env bash
set -eux

pip install -r requirements.txt
playwright install --with-deps chromium
