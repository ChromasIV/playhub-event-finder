@echo off
:: Navigate to the script's directory
cd /d "%~dp0"

:: Run the Python script to fetch new events and update index.html
python find_events.py

:: Option to automatically open the report in the default browser (can be commented out if run in background)
:: start "" "index.html"
