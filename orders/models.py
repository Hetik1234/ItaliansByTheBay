from django.db import models
from django.contrib.auth.models import User
from menu.models import MenuItem
from decimal import Decimal

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Delivered', 'Delivered'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    def save(self, *args, **kwargs):
        """Ensure consistent capitalization of order status."""
        if self.status:
            self.status = self.status.capitalize()   
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username} ({self.status})"

    def update_total(self):
        total = sum(item.subtotal() for item in self.orderitem_set.all())
        self.total_price = Decimal(total)
        self.save(update_fields=['total_price'])

    def total_amount(self):
        return self.total_price


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.update_total()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.order.update_total()
