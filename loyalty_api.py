import requests
import time

# --- CONFIGURATION ---
BASE_URL = "http://loyalty-api.us-east-1.elasticbeanstalk.com/api/v1"
TEST_USER = {
    "email": "diagnostics123@example.com",
    "username": "diag_tester_123",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User"
}
# Using a dummy ID for the URL since your Django app passes its own user.id
TEST_USER_ID = 9999 

print("=========================================")
print(" STARTING LOYALTY API DIAGNOSTICS...")
print("=========================================\n")

# --- 1. TEST REGISTRATION ---
print(" STEP 1: Testing User Registration (/users/)")
try:
    reg_resp = requests.post(f"{BASE_URL}/users/", json=TEST_USER, timeout=10)
    print(f"Status Code: {reg_resp.status_code}")
    print(f"Response: {reg_resp.text}")
except Exception as e:
    print(f" CRASH: Could not connect to Registration endpoint. Error: {e}")

time.sleep(1) # Brief pause so we don't hammer the API

# --- 2. TEST LOGIN & JWT TOKEN ---
print("\n STEP 2: Testing Login (/auth/token/)")
access_token = None
try:
    login_payload = {"email": TEST_USER["email"], "password": TEST_USER["password"]}
    login_resp = requests.post(f"{BASE_URL}/auth/token/", json=login_payload, timeout=10)
    print(f"Status Code: {login_resp.status_code}")
    
    if login_resp.status_code == 200:
        access_token = login_resp.json().get("access")
        print(" SUCCESS: JWT Token received!")
    else:
        print(f"Response: {login_resp.text}")
        print(" FAILED: Could not get token. Stopping tests here.")
        exit()
except Exception as e:
    print(f" CRASH: Could not connect to Login endpoint. Error: {e}")
    exit()

time.sleep(1)

# Set up headers for the secured endpoints
HEADERS = {"Authorization": f"Bearer {access_token}"}

# --- 3. TEST BALANCE ---
print("\n STEP 3: Testing Balance (/points/{id}/balance/)")
try:
    bal_resp = requests.get(f"{BASE_URL}/points/{TEST_USER_ID}/balance/", headers=HEADERS, timeout=10)
    print(f"Status Code: {bal_resp.status_code}")
    print(f"Response: {bal_resp.text}")
except Exception as e:
    print(f" CRASH: Could not connect to Balance endpoint. Error: {e}")

time.sleep(1)

# --- 4. TEST EARNING POINTS ---
print("\n STEP 4: Testing Earning Points (/points/{id}/earn/)")
try:
    earn_payload = {
        "points": 50,
        "description": "Diagnostic API Test",
        "source": "Python Script"
    }
    earn_resp = requests.post(f"{BASE_URL}/points/{TEST_USER_ID}/earn/", json=earn_payload, headers=HEADERS, timeout=10)
    print(f"Status Code: {earn_resp.status_code}")
    print(f"Response: {earn_resp.text}")
except Exception as e:
    print(f" CRASH: Could not connect to Earn endpoint. Error: {e}")

print("\n=========================================")
print(" DIAGNOSTICS COMPLETE.")
print("=========================================")