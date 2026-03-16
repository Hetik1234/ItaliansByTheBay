from django.shortcuts import render, get_object_or_404
from .models import Category, MenuItem
from orders.models import OrderItem
from django.db.models import Sum

def home(request):
    categories = Category.objects.all()
    # popular items: top 3 by sum(quantity)
    popular = (
        OrderItem.objects
        .values('item', 'item__name', 'item__image')
        .annotate(total_ordered=Sum('quantity'))
        .order_by('-total_ordered')[:3]
    )
    return render(request, 'menu/home.html', {'categories': categories, 'popular': popular})

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    items = category.items.all()
    return render(request, 'menu/category_detail.html', {'category': category, 'items': items})

def item_detail(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    return render(request, 'menu/item_detail.html', {'item': item})
