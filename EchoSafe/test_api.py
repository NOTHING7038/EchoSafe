#!/usr/bin/env python3
"""Test script for EchoSafe API"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_submit_report():
    """Test report submission"""
    print("\n=== Testing Report Submission ===")
    
    report_data = {
        "report_text": "There is a serious threat and physical violence concern in our office"
    }
    
    response = requests.post(f"{BASE_URL}/api/submit_report", json=report_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        case_id = response.json()["case_id"]
        return case_id
    return None

def test_register_hr():
    """Test HR registration"""
    print("\n=== Testing HR Registration ===")
    
    hr_data = {
        "username": "hr_investigator_001",
        "password": "SecurePassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/api/hr/register", json=hr_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_hr_login():
    """Test HR login"""
    print("\n=== Testing HR Login ===")
    
    login_data = {
        "username": "hr_investigator_001",
        "password": "SecurePassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/api/hr/login", json=login_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        token = response.json()["token"]
        return token
    return None

def test_view_dashboard(token):
    """Test dashboard view"""
    print("\n=== Testing Dashboard ===")
    
    params = {"token": token}
    response = requests.get(f"{BASE_URL}/api/hr/dashboard", params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    print("🔐 EchoSafe API Test Suite")
    print("=" * 50)
    
    # Test 1: Submit Report
    case_id = test_submit_report()
    
    # Test 2: Register HR User
    test_register_hr()
    
    # Test 3: Login HR User
    token = test_hr_login()
    
    # Test 4: View Dashboard
    if token:
        test_view_dashboard(token)
    
    print("\n" + "=" * 50)
    print("✅ API Tests Completed!")
