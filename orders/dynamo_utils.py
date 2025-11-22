import boto3
from decimal import Decimal
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

DDB_TABLE = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DDB_TABLE)


def save_order_to_dynamodb(order):
    try:
        order_items = []

        for oi in order.orderitem_set.all():   # FIXED
            order_items.append({
                "item_name": oi.item.name,
                "quantity": oi.quantity,
                "price": str(oi.price)
            })

        item = {
            "user_id": str(order.user.id),
            "order_id": str(order.id),
            "created_at": order.created_at.isoformat(),
            "status": order.status,
            "total": str(order.total_amount()),
            "items": order_items,
        }

        table.put_item(Item=item)
        return True

    except Exception as e:
        logger.error(f"Failed to save order {order.id} to DynamoDB: {e}")
        return False
