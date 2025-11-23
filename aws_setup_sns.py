import boto3
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TOPIC_NAME = "order-notification-topic"


def setup_sns_topic():
    """Create SNS topic (or fetch if already exists)."""
    sns = boto3.client("sns", region_name=AWS_REGION)

    print("Creating or fetching SNS topic...")

    try:
        response = sns.create_topic(Name=TOPIC_NAME)
        topic_arn = response["TopicArn"]

        print(f"Topic ready: {topic_arn}")
        print("Add this to your .env file:")
        print(f"AWS_SNS_TOPIC_ARN={topic_arn}")

        return topic_arn

    except Exception as e:
        print("Error creating SNS topic:", e)
        return None


def main():
    print("Starting SNS setup...")
    setup_sns_topic()
    print("SNS setup complete.")


if __name__ == "__main__":
    main()
