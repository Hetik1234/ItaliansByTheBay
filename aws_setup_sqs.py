import boto3
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TOPIC_ARN = os.getenv("AWS_SNS_TOPIC_ARN")

sqs = boto3.client("sqs", region_name=AWS_REGION)
sns = boto3.client("sns", region_name=AWS_REGION)

QUEUE_NAME = "order-events-queue"

def main():
    print("Creating SQS queue...")

    # FIFO not required unless needed
    resp = sqs.create_queue(
        QueueName=QUEUE_NAME,
        Attributes={
            "VisibilityTimeout": "60"
        }
    )
    queue_url = resp["QueueUrl"]

    print("SQS queue created:", queue_url)

    # Get queue ARN
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['QueueArn']
    )
    queue_arn = attrs["Attributes"]["QueueArn"]
    print("Queue ARN:", queue_arn)

    print("Subscribing SQS queue to SNS topic:", TOPIC_ARN)
    sns.subscribe(
        TopicArn=TOPIC_ARN,
        Protocol="sqs",
        Endpoint=queue_arn
    )

    print("Allowing SNS to publish to SQS...")
    policy = f"""
    {{
      "Version": "2012-10-17",
      "Statement": [
        {{
          "Effect": "Allow",
          "Principal": "*",
          "Action": "SQS:SendMessage",
          "Resource": "{queue_arn}",
          "Condition": {{
            "ArnEquals": {{"aws:SourceArn":"{TOPIC_ARN}"}}
          }}
        }}
      ]
    }}
    """

    sqs.set_queue_attributes(
        QueueUrl=queue_url,
        Attributes={"Policy": policy}
    )

    print("SQS setup complete.")

if __name__ == "__main__":
    main()
