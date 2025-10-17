#!/usr/bin/env bash
set -e
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright

echo "Installing pip and Playwright..."
pip install --upgrade pip
pip install playwright

echo "Installing Chromium..."
playwright install chromium

echo "Build completed successfully."
