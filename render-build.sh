#!/usr/bin/env bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (Chromium only)
playwright install chromium
