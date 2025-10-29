from decimal import Decimal
from .exceptions import CartItemNotFound

class Cart:
    """
    Session-based cart utility. Stores items as:
    session['cart'] = {
      '<item_id>': {'name': ..., 'price': '12.50', 'quantity': 2},
      ...
    }
    """

    SESSION_KEY = 'cart'

    def __init__(self, session):
        self.session = session
        self.cart = session.get(self.SESSION_KEY, {})

    def add(self, item_id, name, price, quantity=1):
        item_id = str(item_id)
        if item_id in self.cart:
            self.cart[item_id]['quantity'] += quantity
        else:
            self.cart[item_id] = {'name': name, 'price': str(price), 'quantity': quantity}
        self.save()

    def remove(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()
        else:
            raise CartItemNotFound(f"Item {item_id} not in cart")

    def clear(self):
        self.session[self.SESSION_KEY] = {}
        self.session.modified = True
        self.cart = {}

    def total_price(self):
        total = Decimal('0.00')
        for v in self.cart.values():
            total += Decimal(v['price']) * v['quantity']
        return total

    def count_items(self):
        return sum(v['quantity'] for v in self.cart.values())

    def get_items(self):
        return [
            {
                'id': item_id,
                'name': v['name'],
                'price': Decimal(v['price']),
                'quantity': v['quantity'],
                'subtotal': Decimal(v['price']) * v['quantity']
            }
            for item_id, v in self.cart.items()
        ]

    def save(self):
        self.session[self.SESSION_KEY] = self.cart
        self.session.modified = True
