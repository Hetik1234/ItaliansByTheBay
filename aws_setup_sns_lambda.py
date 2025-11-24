"""
Creates:
 - SNS topic (order-notification-topic)
 - SQS queue (italians-order-queue)
 - Lambda function (orderPlacedHandler)
 - Connections: SNS -> SQS -> Lambda
 - Cleanup: Removes old direct SNS->Lambda subscriptions
"""
import boto3
import json
import os
import time
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SNS_NAME = "order-notification-topic"
SQS_NAME = "italians-order-queue"
LAMBDA_NAME = "orderPlacedHandler"
LAMBDA_ZIP = "lambda_build/lambda_payload.zip"
LAMBDA_RUNTIME = "python3.9"
LAMBDA_HANDLER = "lambda_function.lambda_handler"
ROLE_NAME = os.getenv("LAMBDA_ROLE_NAME", "LabRole") 

session = boto3.Session(region_name=AWS_REGION)
sns = session.client("sns")
sqs = session.client("sqs")
iam = session.client("iam")
lambda_client = session.client("lambda")

def ensure_topic():
    resp = sns.create_topic(Name=SNS_NAME)
    print("SNS Topic ARN:", resp["TopicArn"])
    return resp["TopicArn"]

def ensure_queue():
    # Create Queue
    resp = sqs.create_queue(QueueName=SQS_NAME)
    queue_url = resp["QueueUrl"]
    
    # Get ARN
    attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])
    queue_arn = attrs["Attributes"]["QueueArn"]
    
    print("SQS Queue URL:", queue_url)
    print("SQS Queue ARN:", queue_arn)
    return queue_url, queue_arn

def set_sqs_policy_allow_sns(queue_url, queue_arn, sns_arn):
    # Policy allowing SNS topic to write to this SQS queue
    policy = {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {"AWS": "*"},
          "Action": "sqs:SendMessage",
          "Resource": queue_arn,
          "Condition": {"ArnEquals": {"aws:SourceArn": sns_arn}}
        }
      ]
    }
    sqs.set_queue_attributes(
        QueueUrl=queue_url,
        Attributes={"Policy": json.dumps(policy)}
    )
    print("SQS policy updated: SNS can write to SQS.")

def subscribe_sns_to_sqs(sns_arn, queue_arn):
    resp = sns.subscribe(TopicArn=sns_arn, Protocol="sqs", Endpoint=queue_arn)
    print("Subscribed SNS -> SQS:", resp["SubscriptionArn"])

def remove_direct_sns_lambda_subscription(sns_arn, lambda_arn):
    """
    Finds and deletes any direct subscriptions from SNS to this Lambda
    to ensure we only use the SQS path.
    """
    print("Checking for old Direct SNS -> Lambda subscriptions to remove...")
    paginator = sns.get_paginator('list_subscriptions_by_topic')
    cleaned = False
    
    for page in paginator.paginate(TopicArn=sns_arn):
        for sub in page['Subscriptions']:
            if sub['Protocol'] == 'lambda' and sub['Endpoint'] == lambda_arn:
                print(f"Removing old direct subscription: {sub['SubscriptionArn']}")
                try:
                    sns.unsubscribe(SubscriptionArn=sub['SubscriptionArn'])
                    cleaned = True
                except Exception as e:
                    print(f"Error unsubscribing: {e}")
    
    if not cleaned:
        print("No direct SNS -> Lambda subscriptions found (Good).")

def create_or_get_lambda_role_arn(role_name):
    try:
        r = iam.get_role(RoleName=role_name)
        print(f"Using existing IAM role: {role_name}")
        return r["Role"]["Arn"]
    except ClientError as e:
        raise RuntimeError(f"Role {role_name} not found. Ensure LabRole exists. Error: {e}")

def create_or_update_lambda(lambda_name, role_arn):
    if not os.path.exists(LAMBDA_ZIP):
        # Fallback: try to zip it now if it doesn't exist
        print(f"Zip not found at {LAMBDA_ZIP}. Attempting to zip lambda_build/lambda_function.py...")
        os.system("zip -j lambda_build/lambda_payload.zip lambda_build/lambda_function.py")
    
    with open(LAMBDA_ZIP, "rb") as f:
        zip_bytes = f.read()

    try:
        lambda_client.get_function(FunctionName=lambda_name)
        print("Lambda exists, updating code...")
        lambda_client.update_function_code(
            FunctionName=lambda_name,
            ZipFile=zip_bytes
        )
        print("Lambda code updated.")
    except lambda_client.exceptions.ResourceNotFoundException:
        print("Creating Lambda function...")
        resp = lambda_client.create_function(
            FunctionName=lambda_name,
            Runtime=LAMBDA_RUNTIME,
            Role=role_arn,
            Handler=LAMBDA_HANDLER,
            Code={'ZipFile': zip_bytes},
            Timeout=10,
            MemorySize=128,
            Publish=True
        )
        print("Lambda created:", resp["FunctionArn"])
    
    # Wait for Active state
    print("Waiting for Lambda to be Active...")
    for _ in range(10):
        try:
            state = lambda_client.get_function(FunctionName=lambda_name)["Configuration"]["State"]
            if state == "Active":
                break
        except:
            pass
        time.sleep(1)

def connect_sqs_to_lambda(lambda_name, queue_arn):
    """
    Creates an Event Source Mapping so SQS triggers the Lambda.
    """
    print(f"Connecting SQS ({queue_arn}) -> Lambda ({lambda_name})...")
    try:
        # check if mapping exists
        mappings = lambda_client.list_event_source_mappings(
            FunctionName=lambda_name,
            EventSourceArn=queue_arn
        )
        
        if mappings['EventSourceMappings']:
            print("Event mapping already exists.")
            # Ensure it is enabled
            uuid = mappings['EventSourceMappings'][0]['UUID']
            lambda_client.update_event_source_mapping(UUID=uuid, Enabled=True)
        else:
            lambda_client.create_event_source_mapping(
                EventSourceArn=queue_arn,
                FunctionName=lambda_name,
                Enabled=True,
                BatchSize=10
            )
            print("Created new SQS trigger for Lambda.")
            
    except ClientError as e:
        print("Error connecting SQS to Lambda:", e)

def main():
    print("--- Setting up SNS -> SQS -> Lambda ---")
    
    # 1. Setup SNS
    sns_arn = ensure_topic()
    
    # 2. Setup SQS
    queue_url, queue_arn = ensure_queue()
    set_sqs_policy_allow_sns(queue_url, queue_arn, sns_arn)
    subscribe_sns_to_sqs(sns_arn, queue_arn)

    # 3. Setup Lambda
    role_arn = create_or_get_lambda_role_arn(ROLE_NAME)
    
    # (Create zip on the fly if needed)
    if not os.path.exists("lambda_build"):
        os.makedirs("lambda_build")
    os.system("zip -j lambda_build/lambda_payload.zip lambda_build/lambda_function.py")
    
    create_or_update_lambda(LAMBDA_NAME, role_arn)
    
    # Get Lambda ARN for cleanup
    lambda_arn = lambda_client.get_function(FunctionName=LAMBDA_NAME)["Configuration"]["FunctionArn"]

    # 4. Trigger: SQS -> Lambda
    connect_sqs_to_lambda(LAMBDA_NAME, queue_arn)

    # 5. CLEANUP: Remove old direct SNS -> Lambda connection
    remove_direct_sns_lambda_subscription(sns_arn, lambda_arn)

    print("\nSetup complete!")
    print(f"1. Django sends to SNS: {sns_arn}")
    print(f"2. SNS forwards to SQS: {queue_url}")
    print(f"3. SQS triggers Lambda: {LAMBDA_NAME}")

if __name__ == "__main__":
    main()