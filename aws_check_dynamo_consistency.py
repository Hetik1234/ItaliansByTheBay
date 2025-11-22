import boto3
import os
import json
from decimal import Decimal
from django.conf import settings
import django

# Initialize Django ORM (required for external script)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'italians_by_the_bay.settings')
django.setup()

from orders.models import Order, OrderItem
from django.contrib.auth.models import User


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")

ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = ddb.Table(TABLE_NAME)


def fetch_dynamo_orders():
    resp = table.scan()
    return resp.get("Items", [])


def order_to_dict(order):
    return {
        "user_id": str(order.user.id),
        "order_id": str(order.id),
        "created_at": order.created_at.isoformat(),
        "status": order.status,
        "total": str(order.total_price),
        "items": [
            {
                "item_name": oi.item.name,
                "quantity": oi.quantity,
                "price": str(oi.price)
            }
            for oi in order.orderitem_set.all()
        ]
    }


def check_consistency():
    print("=== DynamoDB Consistency Check ===")

    sql_orders = Order.objects.all()
    dynamo_orders = fetch_dynamo_orders()

    # Convert to dict for quick lookups
    dynamo_by_id = { d["order_id"]: d for d in dynamo_orders }

    missing = []
    mismatched = []
    extra = []

    # 1️⃣ Find missing or mismatched orders
    for order in sql_orders:
        oid = str(order.id)

        if oid not in dynamo_by_id:
            missing.append(order)
            continue

        sql_data = order_to_dict(order)
        dyn_data = dynamo_by_id[oid]

        # Compare fields
        if sql_data["status"] != dyn_data.get("status") or sql_data["total"] != dyn_data.get("total"):
            mismatched.append(order)

    # 2️⃣ Find extra entries in DynamoDB
    for dyn in dynamo_orders:
        if not Order.objects.filter(id=dyn["order_id"]).exists():
            extra.append(dyn)

    # --- Print report ---
    print("\nMissing orders:", [o.id for o in missing])
    print("Mismatched orders:", [o.id for o in mismatched])
    print("Extra records:", [e["order_id"] for e in extra])

    # --- Fix missing ---
    for o in missing:
        print(f"→ Adding missing order {o.id}")
        table.put_item(Item=order_to_dict(o))

    # --- Fix mismatched ---
    for o in mismatched:
        print(f"→ Updating mismatched order {o.id}")
        table.put_item(Item=order_to_dict(o))

    # --- Delete extra ---
    for e in extra:
        print(f"→ Deleting orphaned DynamoDB record {e['order_id']}")
        table.delete_item(
            Key={"user_id": e["user_id"], "order_id": e["order_id"]}
        )

    print("\n✔ Consistency check complete.")


if __name__ == "__main__":
    check_consistency()
