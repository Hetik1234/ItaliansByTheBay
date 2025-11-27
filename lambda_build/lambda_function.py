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

    records = event.get("Records", [])

    for r in records:
        body = json.loads(r.get("body", "{}"))
        message = body.get("Message", "")

        print("Processing:", message)

        order_id, amount = parse_order_message(message)
        push_metrics(order_id, amount)
        export_daily_json(amount)

    return {"status": "ok"}
