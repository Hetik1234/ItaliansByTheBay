import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from decimal import Decimal
from django.template.loader import render_to_string

from .models import Order, OrderItem
from cart_utils.cart import Cart
from menu.models import MenuItem
from .loyalty_utils import award_points, get_loyalty_balance, redeem_points

# --- API HELPER FUNCTION ---
def trigger_cloudmail_api(to_email, subject, html_content):
    """
    Helper function to send emails via our external CloudMail API.
    Returns a tuple: (Success_Boolean, Response_Message)
    """
    payload = {
        "to_email": to_email,
        "subject": subject,
        "message": html_content, 
        "from_name": "Italians by the Bay",
        "reply_to": "support@italiansbythebay.com"
    }
    
    try:
        api_response = requests.post(settings.CLOUDMAIL_API_URL, data=payload)
        if api_response.status_code == 200:
            return True, "Email sent successfully"
        return False, api_response.text
    except requests.exceptions.RequestException as e:
        return False, f"API Connection Error: {str(e)}"

def get_inr_exchange_rate():
    """
    Fetches the live EUR to INR exchange rate from a free public API.
    No API key required!
    """
    # This is a highly reliable, free, open-source currency CDN
    url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            # The API returns data['eur']['inr']
            return data.get('eur', {}).get('inr', 100.00) 
    except Exception as e:
        print(f"Currency API Error: {e}")
        
    # Always return a safe fallback (approx 90 INR to 1 EUR) so your app never crashes!
    return 100.00
# --- CART MANAGEMENT ---

@login_required
def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    cart = Cart(request.session)
    cart.add(item_id=item.id, name=item.name, price=float(item.price), quantity=1)
    messages.success(request, f"{item.name} added to cart.")
    return redirect('orders:view_cart')

@login_required
def remove_from_cart(request, item_id):
    cart = Cart(request.session)
    try:
        cart.remove(item_id)
        messages.info(request, "Item removed from cart.")
    except Exception:
        messages.error(request, "Unable to remove item.")
    return redirect('orders:view_cart')

@login_required
def update_cart_quantity(request, item_id):
    if request.method == 'POST':
        new_qty = int(request.POST.get('quantity', 1))
        cart = request.session.get('cart', {})

        if str(item_id) in cart:
            if new_qty > 0:
                cart[str(item_id)]['quantity'] = new_qty
                messages.success(request, "Quantity updated successfully.")
            else:
                del cart[str(item_id)]
                messages.info(request, "Item removed from cart.")

            request.session['cart'] = cart

    return redirect('orders:view_cart')

@login_required
def view_cart(request):
    cart = Cart(request.session)
    subtotal = float(cart.total_price())
    
    # Grab the discount from the session (default to 0)
    discount = request.session.get('loyalty_discount', 0.00)
    
    # Ensure total doesn't go below 0
    final_total = max(0, subtotal - discount)
    
    # Get balance using the UUID
    loyalty_token = request.session.get('loyalty_token')
    api_uuid = request.session.get('loyalty_api_uuid')
    
    balance = get_loyalty_balance(loyalty_token, api_uuid) if (loyalty_token and api_uuid) else 0

    # --- NEW: Public Currency API Integration ---
    exchange_rate = get_inr_exchange_rate()
    # Calculate INR and round to 2 decimal places
    inr_total = round(final_total * exchange_rate, 2)
    # Round the exchange rate just to make it look clean on the frontend
    clean_rate = round(exchange_rate, 2)

    return render(request, 'orders/cart.html', {
        'cart_items': cart.get_items(),
        'subtotal': subtotal,
        'discount': discount,
        'final_total': final_total,
        'points_balance': balance,
        'inr_total': inr_total,         # Send the INR amount to the HTML
        'exchange_rate': clean_rate     # Send the live rate to the HTML
    })
# --- CHECKOUT & ORDERS ---

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('menu:home')

    # --- Calculate points BEFORE we clear the cart ---
    cart_obj = Cart(request.session)
    points_earned = int(cart_obj.total_price())

    # 1. Create order
    order = Order.objects.create(user=request.user, status="Pending")

    # 2. Create order items
    for item_id, item_data in cart.items():
        try:
            menu_item = MenuItem.objects.get(id=item_id)
        except MenuItem.DoesNotExist:
            continue

        OrderItem.objects.create(
            order=order,
            item=menu_item,
            quantity=int(item_data.get('quantity', 1)),
            price=Decimal(str(menu_item.price))
        )

    # 3. Clear cart
    request.session.pop('cart', None)
    request.session.pop('loyalty_discount', None)
    
    # --- LOYALTY API INTEGRATION (Using UUID) ---
    loyalty_token = request.session.get('loyalty_token')
    api_uuid = request.session.get('loyalty_api_uuid')
    
    if loyalty_token and api_uuid:
        print(f"Awarding {points_earned} points to API User {api_uuid}...")
        success, msg = award_points(loyalty_token, api_uuid, points_earned)
        
        if success:
            messages.success(request, f"🎉 You earned {points_earned} loyalty points!")
        else:
            print(f"Loyalty API Error: {msg}")
    else:
        print("WARNING: No loyalty token or UUID found in session. Points not awarded.")

    # 4. Trigger Order Confirmation Email
    try:
        context = {
            'username': request.user.username,
            'order_id': order.id,
            'site_name': 'Italians by the Bay',
        }
        # Render the confirmation template
        html_body = render_to_string('emails/order_confirmation.html', context)
        
        success, msg = trigger_cloudmail_api(
            to_email=request.user.email,
            subject=f"Order Received! Confirmation #{order.id}",
            html_content=html_body
        )
        
        if not success:
            print(f"Checkout Email Warning: {msg}")
            
    except Exception as e:
        print(f"Checkout Email Template Error: {e}")

    messages.success(request, f"Order #{order.id} placed successfully!")
    return redirect('orders:checkout_success', order.id)

@login_required
def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/checkout_success.html', {'order': order})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})

@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status.lower() == 'pending':
        order.delete()
        messages.success(request, f"Order #{order_id} deleted successfully.")
    else:
        messages.warning(request, "Only pending orders can be deleted.")

    return redirect('orders:my_orders')

# --- ADMIN VIEWS ---

@staff_member_required
def all_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'orders/all_orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
    })

@staff_member_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status and new_status.capitalize() != order.status:
            order.status = new_status.capitalize()
            order.save()

            try:
                context = {
                    'username': order.user.username,
                    'order_id': order.id,
                    'status': order.status,
                    'site_name': 'Italians by the Bay',
                }
                
                html_body = render_to_string('emails/order_status_update.html', context)

                success, msg = trigger_cloudmail_api(
                    to_email=order.user.email,
                    subject=f"Your Order #{order.id} Status Updated",
                    html_content=html_body
                )

                if success:
                    messages.success(request, f"Order #{order.id} updated and notification sent.")
                else:
                    messages.warning(request, f"Order updated, but email API failed: {msg}")

            except Exception as e:
                messages.warning(request, "Order updated, but email notification failed internally.")
                print("INTERNAL TEMPLATE ERROR:", e)
        else:
            messages.info(request, "No change in order status.")

        return redirect('orders:all_orders')

    messages.warning(request, "Invalid request.")
    return redirect('orders:all_orders')
    
@login_required
def apply_loyalty_discount(request):
    """Handles the user clicking 'Redeem 50 points' in the cart."""
    loyalty_token = request.session.get('loyalty_token')
    api_uuid = request.session.get('loyalty_api_uuid')
    
    if not loyalty_token or not api_uuid:
        messages.warning(request, "Loyalty system unavailable. Please log in again.")
        return redirect('orders:view_cart')

    # 1. Check their balance first
    current_balance = get_loyalty_balance(loyalty_token, api_uuid)
    
    if current_balance >= 50:
        # 2. Try to redeem the points via the API
        success, msg = redeem_points(loyalty_token, api_uuid, 50)
        
        if success:
            # 3. Apply the €5 discount to their session
            request.session['loyalty_discount'] = 5.00
            messages.success(request, "🎉 50 points redeemed! €5.00 discount applied to your cart.")
        else:
            messages.error(request, f"Could not redeem points: {msg}")
    else:
        messages.warning(request, f"You only have {current_balance} points. 50 required to redeem.")

    return redirect('orders:view_cart')