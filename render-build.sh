#!/usr/bin/env bash
set -euo pipefail

echo "Upgrade pip and install python deps..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Install Playwright browsers to /tmp/playwright..."
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright
# Install playwright python package (ensures CLI available)
pip install playwright
# Install Chromium and required libs into user-writable path
playwright install --with-deps chromium

echo "Build script finished."
