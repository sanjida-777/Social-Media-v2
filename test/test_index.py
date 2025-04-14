import requests
import json

def test_index_with_login():
    """
    Test accessing the index page after logging in
    """
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Login first
    login_url = 'http://localhost:5000/auth/api/login'
    login_data = {
        'email': 'test@example.com',
        'password': 'test_hash'
    }
    
    # Make the login request
    login_response = session.post(
        login_url,
        json=login_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Login status code: {login_response.status_code}")
    print(f"Login response: {login_response.text}")
    
    # Now try to access the index page with the same session
    index_response = session.get('http://localhost:5000/')
    
    print(f"Index status code: {index_response.status_code}")
    print(f"Index page title: {index_response.text[:200]}...")  # Just print the beginning to see the title

if __name__ == "__main__":
    test_index_with_login()
