import requests
import json
import sys
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
BASE_URL = "https://central.local"
EMAIL = "m"
PASSWORD = "="
PROJECT_ID = "1"
# ---------------------

def get_token():
    print(f"1. Logging in to {BASE_URL}/v1/projects/{PROJECT_ID}/app-users/login ...")
    payload = {
        "username": EMAIL,
        "password": PASSWORD,
        "deviceId": "python-debug-client"
    }
    try:
        r = requests.post(f"{BASE_URL}/v1/projects/{PROJECT_ID}/app-users/login", json=payload, verify=False)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            token = r.json().get('token')
            print(f"Login Successful! Token: {token[:10]}...")
            return token
        else:
            print(f"Login Failed: {r.text}")
            return None
    except Exception as e:
        print(f"Login Error: {e}")
        return None

def check_api(token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print(f"\n--- Debugging ODK Central API ---")
    print(f"Project ID: {PROJECT_ID}")
    print("-" * 30)

    # 1. Try listing projects
    print(f"\n2. Testing GET /v1/projects ...")
    try:
        r = requests.get(f"{BASE_URL}/v1/projects", headers=headers, verify=False)
        print(f"Status Code: {r.status_code}")
        print(f"Response Body: {r.text}")
        if r.status_code == 200:
            try:
                projects = r.json()
                found = any(str(p.get('id')) == PROJECT_ID for p in projects)
                print(f"Found Project {PROJECT_ID} in list? {found}")
            except Exception:
                print("Response is not JSON or empty.")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Try specific project
    print(f"\n3. Testing GET /v1/projects/{PROJECT_ID} ...")
    try:
        r = requests.get(f"{BASE_URL}/v1/projects/{PROJECT_ID}", headers=headers, verify=False)
        print(f"Status Code: {r.status_code}")
        print(f"Response Body: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        check_api(token)
    else:
        print("Could not proceed without token.")
