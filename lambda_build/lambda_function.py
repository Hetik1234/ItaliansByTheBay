import json
import re
import os
import boto3
from datetime import datetime, date

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)

S3_BUCKET = os.getenv("ANALYTICS_BUCKET", "italians-by-the-bay-analytics")

def parse_order_message(message):
    try:
        order_id = "unknown"
        amount = 0.0

        id_match = re.search(r"#(\d+)", message)
        if id_match:
            order_id = id_match.group(1)

        amount_match = re.search(r'€\s?([0-9]+(?:[.,][0-9]{1,2})?)', message)
        if amount_match:
            amount = float(amount_match.group(1).replace(",", "."))

        return order_id, amount
    except:
        return "unknown", 0.0


def push_metrics(order_id, amount):
    cloudwatch.put_metric_data(
        Namespace="ItaliansByTheBay/Orders",
        MetricData=[
            {"MetricName": "OrdersCount", "Value": 1},
            {"MetricName": "Revenue", "Value": amount}
        ]
    )
    print(f"CloudWatch metrics pushed for order #{order_id} amount={amount}")


def export_daily_json(amount):
    """
    Export running daily totals into S3 as JSON.
    """
    today = date.today().strftime("%Y-%m-%d")
    key = f"orders/{today}.json"

    print(f"Exporting analytics to S3: {key}")

    # Load previous file if exists
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        previous = json.loads(response["Body"].read().decode("utf-8"))
        total_orders = previous.get("total_orders", 0) + 1
        total_revenue = previous.get("total_revenue", 0) + amount
    except Exception:
        total_orders = 1
        total_revenue = amount

    output = {
        "date": today,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(output, indent=2),
        ContentType="application/json"
    )

    print("Daily S3 JSON export complete.")


def lambda_handler(event, context):
    print("EVENT RECEIVED")

    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table("OrderAnalytics")

    try:
        records = event.get("Records", [])

        for r in records:
            # Parse SNS message from SQS
            sqs_body = json.loads(r.get("body", "{}"))
            message = sqs_body.get("Message", "")

            order_id, amount = parse_order_message(message)

            # Fetch actual order info from DynamoDB
            try:
                ddb_order = table.get_item(
                    Key={"user_id": "1", "order_id": str(order_id)}
                )
                item = ddb_order.get("Item")

                if not item:
                    print(f"Order {order_id} NOT found in DynamoDB. Skipping...")
                    continue

                real_amount = float(item.get("total", 0))
                print("DynamoDB verified:", item)

            except Exception as e:
                print("DynamoDB lookup failed:", e)
                continue

            # ✔ Push corrected metrics
            push_metrics(order_id, real_amount)

        return {"status": "ok", "count": len(records)}

    except Exception as e:
        print("CRITICAL ERROR:", e)
        raise e
