#!/usr/bin/env bash
set -e
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

echo "Build completed successfully."
