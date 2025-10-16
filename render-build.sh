#!/usr/bin/env bash
set -e  # Stop if any command fails

echo "Installing Playwright browsers..."
pip install --upgrade pip
pip install playwright
playwright install --with-deps chromium

echo "Build completed successfully."
