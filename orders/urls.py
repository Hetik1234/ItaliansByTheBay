from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Cart operations
    path('add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),  # ✅ renamed
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # User orders
    path('my/', views.my_orders, name='my_orders'),
    path('delete/<int:order_id>/', views.delete_order, name='delete_order'),

    # Admin management
    path('all/', views.all_orders, name='all_orders'),
    path('update-order/<int:order_id>/', views.update_order_status, name='update_order_status'),  # ✅ renamed
    path('checkout/success/<int:order_id>/', views.checkout_success, name='checkout_success'),
]
