#!/bin/bash

# Navigate to the script directory
cd "$(dirname "$0")"

# Activate virtual environment if you have one
# source venv/bin/activate

# Run the tracker
# To run with real API, ensure OPENSTATES_API_KEY is set in your environment or added here
# export OPENSTATES_API_KEY="your-key-here"  # Set in your environment

echo "Running State Law Tracker..."
python3 main.py # Running with real API

# Check if report was generated
if [ -f "todays_report.md" ]; then
    echo "Report generated."
    # Optional: Email the report
    # mail -s "Daily Law Report" user@example.com < todays_report.md
else
    echo "No report generated."
fi
