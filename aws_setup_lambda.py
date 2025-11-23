import boto3
import json
import os
import time

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LAMBDA_NAME = "orderPlacedHandler"


def create_lambda_role(iam):
    """
    Since Learner Lab does NOT allow IAM role creation,
    we reuse the pre-existing LabRole.
    """
    try:
        role = iam.get_role(RoleName="LabRole")
        print("Using existing IAM role: LabRole")
        return role["Role"]["Arn"]
    except Exception as e:
        print("ERROR: Unable to load LabRole:", e)
        exit(1)


def create_lambda_function(lambda_client, role_arn):
    """Creates or fetches lambda function."""
    # Basic lambda code
    code = """
import json

def lambda_handler(event, context):
    print("SNS EVENT RECEIVED:")
    print(json.dumps(event))
    return {"status": "ok"}
"""

    try:
        lambda_client.get_function(FunctionName=LAMBDA_NAME)
        print("Lambda function already exists.")
        return True

    except lambda_client.exceptions.ResourceNotFoundException:
        print("Creating Lambda function...")

        zip_bytes = None
        import zipfile
        from io import BytesIO

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("lambda_function.py", code)
        zip_bytes = buffer.getvalue()

        lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime="python3.9",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=10,
            MemorySize=128
        )
        print("Lambda created.")
        return True


def main():
    print("Setting up Lambda...")

    iam = boto3.client("iam", region_name=AWS_REGION)
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)

    role_arn = create_lambda_role(iam)
    create_lambda_function(lambda_client, role_arn)

    print("Lambda setup complete.")


if __name__ == "__main__":
    main()
