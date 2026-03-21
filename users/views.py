import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from orders.loyalty_utils import get_loyalty_balance

# --- MICROSERVICE ENDPOINTS ---
AWS_VERIFY_URL = "http://email-verifier-env.eba-mdagwhcq.us-east-1.elasticbeanstalk.com/api/email/"
AWS_STATUS_URL = "http://email-verifier-env.eba-mdagwhcq.us-east-1.elasticbeanstalk.com/api/status/"
OTP_API_URL = "http://otpapi-env.eba-pjkmm4m3.us-east-1.elasticbeanstalk.com"
CLOUDMAIL_URL = "https://27zlcvmy53.execute-api.us-east-1.amazonaws.com/Prod/api/send/" 
LOYALTY_API_URL = "http://loyalty-api.us-east-1.elasticbeanstalk.com/api/v1"

def register_view(request):
    if request.method == 'POST':
        # 1. Grab the data from your HTML form
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        print("\n--- REGISTRATION DEBUG ---")
        print(f"Extracted Username: {repr(username)}")
        print(f"Extracted Email: {repr(email)}")
        print(f"Extracted Password: {repr(password)}")
        print("--------------------------\n")

        # 2. Hard Safety Check
        if not email or not username or not password:
            messages.error(request, "All fields are required!")
            return render(request, 'users/register.html')

        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "A user with that username or email already exists.")
            return render(request, 'users/register.html')

        # 3. The Email Verifier Bouncer
        try:
            api_resp = requests.post(AWS_VERIFY_URL, json={"email": email})
            
            print(f"Friend's API Status Code: {api_resp.status_code}")
            print(f"Friend's API Raw Response: {api_resp.text}")
            
            if api_resp.status_code != 200:
                messages.error(request, f"Validation error: {api_resp.text}")
                return render(request, 'users/register.html')

            api_data = api_resp.json()
            suggestion = api_data.get('details', {}).get('suggestion')
            if suggestion:
                messages.warning(request, f"Typo detected! Did you mean {suggestion}?")
                return render(request, 'users/register.html')
                
        except Exception as e:
            messages.warning(request, "Validation server is unreachable.")
            print(f"API Error: {e}")
            return render(request, 'users/register.html')

        # 4. Save the user locally
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = False 
        user.save()
        
        # 5. Sync with Loyalty API
        print("\n--- LOYALTY SYNC DEBUG ---")
        loyalty_payload = {
            "email": email,
            "username": username,
            "password": password,
            "password_confirm": password,
            "first_name": username,
            "last_name": "Customer"
        }
        
        try:
            print(f"Registering {email} on Loyalty API...")
            loyalty_resp = requests.post(f"{LOYALTY_API_URL}/register/", json=loyalty_payload)
            if loyalty_resp.status_code in [200, 201]:
                print("SUCCESS: User synced to Loyalty API!")
            else:
                print(f"WARNING: Loyalty API Sync Failed ({loyalty_resp.status_code}): {loyalty_resp.text}")
                
        except Exception as e:
            print(f"CRASH: Loyalty API is unreachable: {e}")
        print("--------------------------\n")

        messages.success(request, "Account created! We've sent a secure link to your inbox. Please verify your email before logging in.")
        return redirect('users:login')
        
    return render(request, 'users/register.html')        
    
def custom_login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get('username') 
        password = request.POST.get('password')

        print("\n--- LOGIN DEBUG X-RAY ---")
        print(f"1. User Typed: {repr(login_input)}")

        # 1. Find the user by EITHER username OR email
        try:
            user = User.objects.get(Q(username=login_input) | Q(email=login_input))
            print(f"3. User Found in DB: {user.username} | is_active: {user.is_active}")
            
        except User.DoesNotExist:
            print("ERROR: No user found with that username or email.")
            messages.error(request, "Invalid credentials.")
            return render(request, 'users/login.html')
        except User.MultipleObjectsReturned:
            print("ERROR: Multiple users found. (This shouldn't happen!)")
            messages.error(request, "Account error. Please contact support.")
            return render(request, 'users/login.html')

        # 2. Check the password
        if user.check_password(password):
            print("4. Password Matched!")
            
            # --- Fetch Loyalty Token & UUID ---
            print("4.5 Fetching Loyalty JWT Token & UUID...")
            try:
                loyalty_token_resp = requests.post(
                    f"{LOYALTY_API_URL}/login/", 
                    json={"username": user.username, "email": user.email, "password": password},
                    timeout=3
                )
                
                if loyalty_token_resp.status_code == 200:
                    token_data = loyalty_token_resp.json()
                    print(f"RAW TOKEN DATA: {token_data}")
                    
                    # Grab the massive UUID their database uses
                    api_user_id = token_data.get('user_id')
                    if api_user_id:
                        request.session['loyalty_api_uuid'] = api_user_id
                        print(f"SUCCESS: Saved Loyalty API UUID: {api_user_id}")

                    # Try to grab the token
                    the_token = token_data.get('token') or token_data.get('access') or token_data.get('jwt')
                    
                    if the_token:
                        request.session['pending_loyalty_token'] = the_token
                        print("SUCCESS: Loyalty Token retrieved and waiting in session.")
                    else:
                        print("WARNING: API didn't give us a token! Falling back to UUID for auth.")
                        request.session['pending_loyalty_token'] = api_user_id 
                else:
                    print(f"WARNING: Could not fetch loyalty token: {loyalty_token_resp.text}")
                    
            except Exception as e:
                print(f"CRASH: Loyalty API unreachable for token: {e}")
            # --------------------------------
            
            # 3. Check if account is locked
            if not user.is_active:
                print("5. Account is locked. Asking API for status...")
                try:
                    status_resp = requests.get(AWS_STATUS_URL, params={"email": user.email})
                    print(f"6. API Status Code: {status_resp.status_code}")
                    print(f"7. API Raw Response: {status_resp.text}")

                    status_data = status_resp.json()
                    
                    if status_resp.status_code == 200 and status_data.get("is_verified") in [True, "true", "True"]:
                        print("SUCCESS: Unlocking account.")
                        user.is_active = True
                        user.save()
                    else:
                        print("DENIED: Not verified yet.")
                        messages.warning(request, "Please click the verification link in your email before logging in.")
                        return render(request, 'users/login.html')
                except Exception as e:
                    print(f"API CRASH: {e}")
                    messages.error(request, "Could not check verification status. Try again later.")
                    return render(request, 'users/login.html')

            # 4. Requesting OTP from FastAPI
            print("8. Requesting OTP from FastAPI...")
            try:
                otp_resp = requests.post(f"{OTP_API_URL}/generate-otp", json={"key": user.email})
                
                if otp_resp.status_code == 200:
                    otp_data = otp_resp.json()
                    the_otp = otp_data.get("otp")
                    
                    # 5. Routing through CloudMail API Gateway
                    email_payload = {
                        "to_email": user.email,
                        "subject": "Your Italians by the Bay Login Code",
                        "message": f"Welcome back!\n\nYour 6-digit login code is: {the_otp}\n\nThis code will expire in 5 minutes.",
                        "from_name": "Italians by the Bay",
                        "reply_to": "support@italiansbythebay.com"
                    }
                    
                    form_files = { "attachments" : ( None ,"" ) }
                    try:
                        print(f"Calling CloudMail API to send email to {user.email}...")
                        mail_resp = requests.post(CLOUDMAIL_URL, data=email_payload, files=form_files)
                        if mail_resp.status_code in [200, 201]:
                            print("SUCCESS: Email handed off to CloudMail API successfully!")
                        else:
                            print(f"CloudMail API Error ({mail_resp.status_code}): {mail_resp.text}")
                            messages.error(request, "Failed to send the email. Please try again.")
                            return render(request, 'users/login.html')
                            
                    except Exception as e:
                        print(f"CloudMail API Crash: {e}")
                        messages.error(request, "Email service is temporarily down.")
                        return render(request, 'users/login.html')
                    
                    # Store the user's ID in their browser session temporarily
                    request.session['pending_user_id'] = user.id
                    return redirect('users:verify_otp')
                    
                else:
                    print(f"OTP Generation Failed: {otp_resp.text}")
                    messages.error(request, "Our security system is currently busy. Try again.")
                    return render(request, 'users/login.html')
                    
            except Exception as e:
                print(f"OTP API Crash: {e}")
                messages.error(request, "2FA Service unreachable.")
                return render(request, 'users/login.html')
            
        else:
            print("ERROR: Password did not match.")
            messages.error(request, "Invalid credentials.")
            return render(request, 'users/login.html')

    return render(request, 'users/login.html')
    
def verify_otp_view(request):
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        messages.warning(request, "Please log in first.")
        return redirect('users:login')

    user = User.objects.get(id=pending_user_id)

    if request.method == 'POST':
        user_otp = request.POST.get('otp')

        print(f"\n--- VERIFY OTP DEBUG ---")
        print(f"Sending OTP {user_otp} for {user.email} to FastAPI...")

        try:
            verify_resp = requests.post(f"{OTP_API_URL}/verify-otp", json={
                "key": user.email,
                "otp": user_otp
            })
            
            if verify_resp.status_code == 200:
                print("SUCCESS: OTP Verified! Handing over the keys.")
                login(request, user)
                
                del request.session['pending_user_id'] 
                
                # Activate the Loyalty Token
                if 'pending_loyalty_token' in request.session:
                    request.session['loyalty_token'] = request.session.pop('pending_loyalty_token')
                    print("SUCCESS: Loyalty Token locked into active session!")
                
                messages.success(request, "Welcome back!")
                return redirect('menu:home') 
            else:
                print(f"ERROR: Invalid/Expired OTP: {verify_resp.text}")
                messages.error(request, "Invalid or expired code. Please try again.")
                
        except Exception as e:
            print(f"Verify API Crash: {e}")
            messages.error(request, "Could not verify code at this time.")

    return render(request, 'users/verify_otp.html', {"email": user.email})

@login_required
def profile_view(request):
    loyalty_token = request.session.get('loyalty_token')
    api_uuid = request.session.get('loyalty_api_uuid')
    
    points_balance = 0
    if loyalty_token and api_uuid:
        print("Fetching loyalty balance for profile...")
        points_balance = get_loyalty_balance(loyalty_token, api_uuid)
    else:
        print("WARNING: No loyalty token or UUID found. User might need to log out and log back in.")

    return render(request, 'users/profile.html', {
        'user': request.user,
        'points_balance': points_balance
    })