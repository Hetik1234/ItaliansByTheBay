# orders/dynamo_dashboard.py
import boto3
from botocore.exceptions import ClientError
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal
from .cloudwatch_utils import get_metric_sum, get_peak_hour

import os


def get_dynamodb_table():
    """
    Always fetch a fresh DynamoDB table object using auto-refreshed Cloud9 credentials.
    Prevents ExpiredTokenException.
    """
    session = boto3.Session()  # Cloud9 automatically rotates credentials
    dynamodb = session.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    table_name = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")
    return dynamodb.Table(table_name)


def fetch_all_orders():
    """
    Fetch all DynamoDB order analytics records safely.
    Returns empty list if table is empty or inaccessible.
    """
    table = get_dynamodb_table()

    try:
        response = table.scan()
        return response.get("Items", [])

    except ClientError as e:
        print("DynamoDB Scan Error:", e)
        return []

    except Exception as e:
        print("Unknown DynamoDB Error:", e)
        return []


def compute_analytics(items):
    """
    Compute useful analytics from the DynamoDB records.
    Returns a dictionary containing summary statistics.
    """

    if not items:
        return {
            "total_orders": 0,
            "total_revenue": "0.00",
            "avg_order_value": "0.00",
            "unique_users": 0,
        }

    total_orders = len(items)
    total_revenue = Decimal("0.00")
    users = set()

    for o in items:
        users.add(o.get("user_id"))
        try:
            total_revenue += Decimal(o.get("total", "0.00"))
        except Exception:
            pass  # Ignore malformed rows

    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0

    return {
        "total_orders": total_orders,
        "total_revenue": str(total_revenue),
        "avg_order_value": str(round(avg_order_value, 2)),
        "unique_users": len(users),
    }


@staff_member_required
def dynamo_dashboard(request):
    items = fetch_all_orders()
    
    # Sort newest → oldest
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    stats = compute_analytics(items)

    # CloudWatch metrics
    cw_orders_24h = get_metric_sum("OrdersCount", hours=24)
    cw_revenue_24h = get_metric_sum("Revenue", hours=24)
    cw_peak = get_peak_hour()

    return render(request, "orders/analytics.html", {
        "items": items,
        "stats": stats,
        "cw_orders_24h": cw_orders_24h,
        "cw_revenue_24h": cw_revenue_24h,
        "cw_peak": cw_peak,
    })