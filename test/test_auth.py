import requests
import json
import sys

# Base URL for the API
BASE_URL = "http://localhost:5000"

def test_registration():
    """Test user registration"""
    print("Testing user registration...")
    
    # Registration data
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    
    # Send registration request
    response = requests.post(f"{BASE_URL}/auth/api/register", json=data)
    
    # Print response
    print(f"Registration status code: {response.status_code}")
    print(f"Registration response: {json.dumps(response.json(), indent=2)}")
    
    # Check if registration was successful
    if response.status_code == 200 and response.json().get("success"):
        print("Registration successful!")
        return True
    else:
        print("Registration failed!")
        return False

def test_login():
    """Test user login"""
    print("\nTesting user login...")
    
    # Login data
    data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    # Send login request
    response = requests.post(f"{BASE_URL}/auth/api/login", json=data)
    
    # Print response
    print(f"Login status code: {response.status_code}")
    print(f"Login response: {json.dumps(response.json(), indent=2)}")
    
    # Check if login was successful
    if response.status_code == 200 and response.json().get("success"):
        print("Login successful!")
        return True
    else:
        print("Login failed!")
        return False

def test_forgot_password():
    """Test forgot password functionality"""
    print("\nTesting forgot password...")
    
    # Forgot password data
    data = {
        "email": "test@example.com"
    }
    
    # Send forgot password request
    response = requests.post(f"{BASE_URL}/auth/forgot-password", data=data)
    
    # Print response
    print(f"Forgot password status code: {response.status_code}")
    
    # Check if the request was successful
    if response.status_code == 200 or response.status_code == 302:
        print("Forgot password request successful!")
        return True
    else:
        print("Forgot password request failed!")
        return False

if __name__ == "__main__":
    # Run tests
    registration_success = test_registration()
    login_success = test_login()
    forgot_password_success = test_forgot_password()
    
    # Check if all tests passed
    if registration_success and login_success and forgot_password_success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)
