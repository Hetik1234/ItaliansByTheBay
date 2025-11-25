import boto3
import os

def publish_sns_message(message):
    session = boto3.Session()
    sns = session.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1"))
    topic_arn = os.getenv("AWS_SNS_TOPIC_ARN")

    if not topic_arn:
        print("[SNS] No topic configured")
        return False

    sns.publish(
        TopicArn=topic_arn,
        Subject="Order Event",
        Message=message
    )
    
    print("[SNS] Message sent:", message)
    return True
