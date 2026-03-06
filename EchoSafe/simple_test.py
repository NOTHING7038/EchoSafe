#!/usr/bin/env python3
"""Quick test for EchoSafe API"""

import requests
import json
import sys

try:
    print("Testing /api/submit_report")
    response = requests.post(
        "http://localhost:8000/api/submit_report",
        json={"report_text": "Test report with threat"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
