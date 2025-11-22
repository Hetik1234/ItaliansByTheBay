# aws_setup_dynamo.py
import os
import time
import json
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")

def get_dynamo_client():
    return boto3.client(
        "dynamodb",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN")
    )

def create_table():
    ddb = get_dynamo_client()

    print("\n" + "="*55)
    print(f"Creating DynamoDB table '{TABLE_NAME}' (if not exists) in {AWS_REGION}")
    print("="*55)

    try:
        # check if exists
        resp = ddb.describe_table(TableName=TABLE_NAME)
        print(f" Table '{TABLE_NAME}' already exists (Status: {resp['Table']['TableStatus']})")
        return True
    except ddb.exceptions.ResourceNotFoundException:
        pass
    except ClientError as e:
        print("Error describing table:", e)
        return False

    try:
        ddb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},   # Partition key
                {"AttributeName": "order_id", "KeyType": "RANGE"}  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "order_id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[{"Key": "project", "Value": "ItaliansByTheBay"}]
        )

        print(" Waiting for table to become ACTIVE...")
        waiter = ddb.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f" Table '{TABLE_NAME}' created and active.")
        return True

    except ClientError as e:
        print("Failed to create table:", e)
        return False

def print_table_info():
    ddb = get_dynamo_client()
    try:
        resp = ddb.describe_table(TableName=TABLE_NAME)
        table = resp["Table"]
        print(json.dumps({
            "TableName": table["TableName"],
            "TableStatus": table["TableStatus"],
            "ItemCount": table.get("ItemCount"),
            "TableArn": table["TableArn"],
            "Region": AWS_REGION
        }, indent=2))
    except Exception as e:
        print("Unable to describe table:", e)

if __name__ == "__main__":
    ok = create_table()
    if ok:
        print_table_info()
    else:
        print("Table creation failed.")
