from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from decimal import Decimal
from .models import Order, OrderItem
from cart_utils.cart import Cart
from menu.models import MenuItem
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


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
    """Display all cart items."""
    cart = Cart(request.session)
    return render(request, 'orders/cart.html', {
        'cart_items': cart.get_items(),
        'total': cart.total_price()
    })


# CHECKOUT & ORDERS
@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('menu:home')

    order = Order.objects.create(user=request.user, status="Pending")

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

    # The total auto-updates via OrderItem.save()
    if 'cart' in request.session:
        del request.session['cart']

    messages.success(request, f"Order #{order.id} placed successfully!")
    return redirect('orders:checkout_success', order.id)


@login_required
def checkout_success(request, order_id):
    """Show success message after placing an order."""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/checkout_success.html', {'order': order})


@login_required
def my_orders(request):
    """Show all orders belonging to the current user."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def delete_order(request, order_id):
    """Allow user to delete their own pending orders."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status.lower() == 'pending':
        order.delete()
        messages.success(request, f"Order #{order_id} deleted successfully.")
    else:
        messages.warning(request, "Only pending orders can be deleted.")
    return redirect('orders:my_orders')


# ADMIN VIEWS
@staff_member_required
def all_orders(request):
    """Admin can view all orders."""
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'orders/all_orders.html', {'orders': orders,
    'status_choices': Order.STATUS_CHOICES,
    })

@staff_member_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Only allow POST requests for updates
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status != order.status:
            order.status = new_status.capitalize()
            order.save()

            # Send email notification using template
            try:
                from django.template.loader import render_to_string
                from django.core.mail import EmailMultiAlternatives

                context = {
                    'username': order.user.username,
                    'order_id': order.id,
                    'status': order.status,
                    'site_name': 'Italians by the Bay',
                }

                html_content = render_to_string('emails/order_status_update.html', context)
                email = EmailMultiAlternatives(
                    subject=f"Order #{order.id} Status Update",
                    body=f"Your order #{order.id} status has been updated to: {order.status}",  # plain text fallback
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[order.user.email],
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

                messages.success(
                    request,
                    f"Order #{order.id} updated to '{order.status}' and email sent to {order.user.email}."
                )

            except Exception as e:
                messages.warning(
                    request,
                    f"Order #{order.id} updated to '{order.status}', but email could not be sent."
                )
                print("EMAIL ERROR:", e)

        else:
            messages.info(request, "No change in status detected.")

        return redirect('orders:all_orders')

    # Safety for GET requests
    messages.warning(request, "You can only update orders from the admin panel.")
    return redirect('orders:all_orders')
