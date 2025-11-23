import boto3
import os
from dotenv import load_dotenv
load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TOPIC_ARN = os.getenv("AWS_SNS_TOPIC_ARN")
LAMBDA_NAME = "orderPlacedHandler"


def main():
    if not TOPIC_ARN:
        print("ERROR: AWS_SNS_TOPIC_ARN missing in .env")
        return

    sns = boto3.client("sns", region_name=AWS_REGION)
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)

    # Get lambda ARN
    func = lambda_client.get_function(FunctionName=LAMBDA_NAME)
    lambda_arn = func["Configuration"]["FunctionArn"]

    print("Subscribing Lambda to SNS topic...")

    sns.subscribe(
        TopicArn=TOPIC_ARN,
        Protocol="lambda",
        Endpoint=lambda_arn
    )

    # Allow SNS to invoke Lambda
    lambda_client.add_permission(
        FunctionName=LAMBDA_NAME,
        StatementId="snsInvokePermission",
        Action="lambda:InvokeFunction",
        Principal="sns.amazonaws.com",
        SourceArn=TOPIC_ARN
    )

    print("Lambda is now subscribed to SNS.")


if __name__ == "__main__":
    main()
