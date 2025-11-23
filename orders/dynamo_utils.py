import boto3
from decimal import Decimal
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")
REGION = os.getenv("AWS_REGION", "us-east-1")


# -------------------------------------------------
# ALWAYS GET FRESH CREDENTIALS
# -------------------------------------------------
def get_fresh_table():
    """
    Cloud9 uses temporary STS credentials that rotate.
    This function ensures every DynamoDB call uses fresh credentials.
    """
    session = boto3.Session()                 # loads new rotating creds
    dynamodb = session.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


# -------------------------------------------------
# SAVE ORDER TO DYNAMODB
# -------------------------------------------------
def save_order_to_dynamodb(order):
    table = get_fresh_table()

    try:
        items = [
            {
                "item_name": oi.item.name,
                "quantity": oi.quantity,
                "price": str(oi.price)
            }
            for oi in order.orderitem_set.all()
        ]

        table.put_item(
            Item={
                "user_id": str(order.user.id),
                "order_id": str(order.id),
                "created_at": order.created_at.isoformat(),
                "status": order.status,
                "total": str(order.total_amount()),
                "items": items,
            }
        )

        return True

    except Exception as e:
        logger.error(f"[DDB SAVE ERROR] Order {order.id}: {e}")
        return False


# -------------------------------------------------
# DELETE ORDER
# -------------------------------------------------
def delete_order_from_dynamodb(order):
    try:
        pk = {
            "user_id": str(order.user.id),
            "order_id": str(order.id)
        }
        table.delete_item(Key=pk)
        return True
    except Exception as e:
        logger.error(f"Failed to delete order {order.id} from DynamoDB: {e}")
        return False

# -------------------------------------------------
# FETCH ALL RECORDS FOR ANALYTICS PAGE
# -------------------------------------------------
def fetch_all_orders():
    table = get_fresh_table()

    try:
        response = table.scan()
        return response.get("Items", [])

    except Exception as e:
        logger.error(f"[DDB SCAN ERROR] {e}")
        return []
