# orders/loyalty_utils.py
import requests

# --- Define the URL directly here! ---
LOYALTY_API_URL = "http://loyalty-api.us-east-1.elasticbeanstalk.com/api/v1"

def award_points(token, user_id, amount):
    """
    Calls the external Loyalty API to award points.
    Returns a tuple: (Success_Boolean, Response_Message)
    """
    url = f"{LOYALTY_API_URL}/earn/"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "user_id": user_id,
        "points": int(amount),
        "description": "Order Checkout",
        "source": "Italians by the Bay"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=3)
        if response.status_code in [200, 201]:
            return True, "Points awarded successfully!"
        return False, response.text
    except requests.exceptions.RequestException as e:
        return False, f"API Connection Error: {str(e)}"
        
def get_loyalty_balance(token, user_id):
    """
    Fetches the current points balance from the Loyalty API.
    Returns the integer balance, or 0 if it fails.
    """
    url = f"{LOYALTY_API_URL}/balance/{user_id}/"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=3)
        print(f"RAW BALANCE API RESPONSE: {response.text}")
        
        if response.status_code == 200:
            # 1. Parse the JSON properly (This fixes your NameError!)
            data = response.json() 
            
            # 2. Grab the exact key we found in your terminal
            return int(data.get("total_points", 0))
            
        else:
            print(f"Failed to fetch balance: {response.text}")
            return 0
            
    except requests.exceptions.RequestException as e:
        print(f"Loyalty API Balance Error: {e}")
        return 0        
def redeem_points(token, user_id, amount, description="Redeemed for €5 discount"):
    """
    Calls the Loyalty API to deduct points from the user's balance.
    """
    url = f"{LOYALTY_API_URL}/redeem/"
    
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json"
    }
    payload = {
        "user_id": user_id,
        "points": int(amount), 
        "description": description
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=3)
        if response.status_code in [200, 201]:
            return True, "Points redeemed successfully!"
        return False, response.text
    except requests.exceptions.Timeout:
        return False, "Loyalty API timed out. Try redeeming again later."
    except requests.exceptions.RequestException as e:
        return False, f"API Connection Error: {str(e)}"