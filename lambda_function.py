import json
import boto3
import os
from datetime import datetime

# AWS clients
dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
ses = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))

# Environment variables
DDB_TABLE = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "hetikchandaria67@gmail.com")


def lambda_handler(event, context):
    """
    Lambda receives SNS message:
    {
        "order_id": 7,
        "user_id": 3,
        "total": "12.90"
    }
    """

    print("=== SNS EVENT RECEIVED ===")
    print(json.dumps(event))

    try:
        sns_record = event["Records"][0]["Sns"]
        message_str = sns_record["Message"]
        message = json.loads(message_str)

        order_id = str(message.get("order_id"))
        user_id = str(message.get("user_id"))
        total = str(message.get("total", "0"))

        # ---------- (B) Save analytics to DynamoDB ----------
        table = dynamodb.Table(DDB_TABLE)

        item = {
            "user_id": user_id,
            "order_id": order_id,
            "received_at": datetime.utcnow().isoformat(),
            "event_type": "order_placed",
            "order_total": total,
        }

        table.put_item(Item=item)
        print(f"[DYNAMODB] Saved analytics for Order #{order_id}")

        # ---------- (C) Log to CloudWatch ----------
        print(f"[CLOUDWATCH] Order #{order_id} processed by Lambda")

        # ---------- (D) Send SES admin email ----------
        subject = f"New Order Received #{order_id}"
        body = (
            f"A new order has been placed.\n\n"
            f"Order ID: {order_id}\n"
            f"User ID: {user_id}\n"
            f"Total Amount: {total}\n"
            f"Processed at: {datetime.utcnow().isoformat()}\n"
        )

        try:
            ses.send_email(
                Source=ADMIN_EMAIL,  # Must be verified in SES sandbox
                Destination={"ToAddresses": [ADMIN_EMAIL]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}},
                },
            )

            print(f"[SES] Email sent to admin: {ADMIN_EMAIL}")

        except Exception as e:
            print(f"[SES ERROR] Could not send email: {e}")

        # ---------- DONE ----------
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Processed order analytics"})
        }

    except Exception as e:
        print("=== ERROR ===")
        print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
