import json
import re
import os
import boto3
from datetime import datetime

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)
print("Lambda init: region", AWS_REGION)

def parse_order_message(message):
    """
    Extracts order ID and Amount from the text string.
    Expected format: "Order #13 placed... total EUR 10.98."
    """
    try:
        order_id = "unknown"
        amount = 0.0
        
        # Regex for ID: Look for # followed by digits
        id_match = re.search(r"#(\d+)", message)
        if id_match:
            order_id = id_match.group(1)
            
        # Regex for Amount: Look for Euro symbol followed by digits, optional dot/comma
        # Matches: €10.98, € 10,98, etc.
        # Note: We keep the symbol in regex to match the input, but logic remains ASCII safe
        amount_match = re.search(r'€\s?([0-9]+(?:[.,][0-9]{1,2})?)', message)
        if amount_match:
            # Replace comma with dot for float conversion (European format handling)
            raw_amount = amount_match.group(1).replace(',', '.')
            amount = float(raw_amount)
            
        return order_id, amount
    except Exception as e:
        print(f"Parse logic error: {e}")
        return "unknown", 0.0

def push_metrics(order_id, amount):
    try:
        cloudwatch.put_metric_data(
            Namespace="ItaliansByTheBay/Orders",
            MetricData=[
                {"MetricName": "OrdersCount", "Value": 1, "Unit": "Count"},
                {"MetricName": "Revenue", "Value": amount, "Unit": "None"}
            ]
        )
        # Removed symbol from log to ensure ASCII compatibility
        print(f"CloudWatch metrics pushed for order #{order_id} (Amount: {amount})")
    except Exception as e:
        print("CloudWatch error:", e)

def lambda_handler(event, context):
    """
    Handles SQS Events. 
    Structure: SQS Event -> Records -> Body (JSON String) -> SNS Message (JSON) -> 'Message' String
    """
    print("EVENT RECEIVED")
    
    try:
        # SQS can send multiple records in one batch
        records = event.get("Records", [])
        
        for r in records:
            # --- VERIFICATION: Prove this came from SQS ---
            event_source = r.get("eventSource")
            sqs_msg_id = r.get("messageId")
            
            if event_source == "aws:sqs":
                print(f"PROOF: Message flowed through SQS. (SQS ID: {sqs_msg_id})")
            else:
                print(f"WARNING: Event Source is '{event_source}', NOT SQS.")
            # ---------------------------------------------

            # 1. Parse the SQS Body (It is a JSON string)
            sqs_body = json.loads(r.get("body", "{}"))
            
            # 2. Extract the inner SNS Message
            # When SNS pushes to SQS, the actual text is in the 'Message' field
            message = sqs_body.get("Message", "")
            
            print(f"Processing Message content: {message}")
            
            # 3. Business Logic
            if message:
                order_id, amount = parse_order_message(message)
                push_metrics(order_id, amount)
            else:
                print("Warning: No 'Message' field found in SQS body")

        return {"status": "ok", "processed_count": len(records)}

    except Exception as e:
        print("CRITICAL LAMBDA ERROR:", e)
        # IMPORTANT: If we raise an exception here, SQS will retry the message.
        raise e