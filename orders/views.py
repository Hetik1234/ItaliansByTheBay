from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from decimal import Decimal
from .models import Order, OrderItem
from cart_utils.cart import Cart
from menu.models import MenuItem
from cloud_notify import send_status_email  # library
from django.template.loader import render_to_string
import logging
from orders.dynamo_utils import save_order_to_dynamodb
from . import dynamo_dashboard
from orders.dynamo_utils import delete_order_from_dynamodb
from orders.sns_utils import publish_sns_message

# CART MANAGEMENT
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
    """Allow user to change quantity directly in the cart screen."""
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
    return render(request, 'orders/cart.html', {
        'cart_items': cart.get_items(),
        'total': cart.total_price()
    })


# CHECKOUT AND ORDERS
@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('menu:home')

    # 1. Create order
    order = Order.objects.create(user=request.user, status="Pending")

    # 2. Add order items
    for item_id, item_data in cart.items():
        try:
            menu_item = MenuItem.objects.get(id=item_id)
        except MenuItem.DoesNotExist:
            continue

        price = Decimal(str(menu_item.price))
        qty = int(item_data.get('quantity', 1))

        OrderItem.objects.create(
            order=order,
            item=menu_item,
            quantity=qty,
            price=price
        )

    # 3. Clear cart
    if 'cart' in request.session:
        del request.session['cart']

    # 4. Save analytics to DynamoDB
    try:
        save_order_to_dynamodb(order)
    except Exception as e:
        print("DYNAMODB ERROR:", e)

    # 5. PUBLISH TO SNS (Order Placed Event)
    import boto3, os
    sns = boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1"))
    topic_arn = os.getenv("AWS_SNS_TOPIC_ARN")

    if topic_arn and topic_arn != "replace_later_after_setup":
        try:
            sns.publish(
                TopicArn=topic_arn,
                Subject="New Order Placed",
                Message=f"Order #{order.id} placed by {order.user.username} with total €{order.total_amount()}."
            )
            print(f"[SNS] Published Order #{order.id}")
        except Exception as e:
            print("[SNS ERROR]:", e)
    else:
        print("[SNS] Skipped — SNS topic ARN not configured yet.")

    # 6. Redirect to success page
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
        # 1. Delete from DynamoDB first
        try:
            delete_order_from_dynamodb(order)
        except Exception as e:
            print("Dynamo delete failed:", e)
        
        try:
            publish_sns_message(f"Order #{order.id} was deleted by {request.user.username}.")
        except Exception as e:
            print("SNS delete error:", e)
        # 2. Delete from SQLite
        order.delete()
        messages.success(request, f"Order #{order_id} deleted successfully.")
    else:
        messages.warning(request, "Only pending orders can be deleted.")
    return redirect('orders:my_orders')

# ADMIN VIEWS
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
    print(f"[DEBUG] update_order_status triggered for order {order_id}, method={request.method}")

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status and new_status.capitalize() != order.status:
            # Update SQL
            order.status = new_status.capitalize()
            order.save()

            # Update DynamoDB
            from orders.dynamo_utils import save_order_to_dynamodb
            save_order_to_dynamodb(order)

            # Clear leftover messages
            storage = messages.get_messages(request)
            for _ in storage:
                pass

            try:
                context = {
                    'username': order.user.username,
                    'order_id': order.id,
                    'status': order.status,
                    'site_name': 'Italians by the Bay',
                }
                html_body = render_to_string('emails/order_status_update.html', context)
                text_body = f"Hi {order.user.username}, your order #{order.id} status has been updated to {order.status}."

                send_status_email(
                    to_email=order.user.email,
                    subject=f"Your Order #{order.id} Status Updated",
                    html_body=html_body,
                    text_body=text_body,
                    fail_silently=False
                )

                messages.success(
                    request,
                    f"Order #{order.id} updated to '{order.status}' and notification sent."
                )

            except Exception as e:
                messages.warning(
                    request,
                    f"Order #{order.id} updated, but notification failed."
                )
                print("NOTIFIER ERROR:", e)

        else:
            messages.info(request, "No change in status detected.")

        return redirect('orders:all_orders')

    messages.warning(request, "You can only update orders from the admin panel.")
    return redirect('orders:all_orders')
