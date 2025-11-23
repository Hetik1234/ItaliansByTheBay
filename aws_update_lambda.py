import boto3
import os
import zipfile

LAMBDA_NAME = "OrderProcessingLambda"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def zip_lambda():
    """Create zip from lambda_build/lambda_function.py"""
    build_dir = "lambda_build"
    zip_path = os.path.join(build_dir, "lambda_payload.zip")
    function_path = os.path.join(build_dir, "lambda_function.py")

    if not os.path.exists(function_path):
        raise FileNotFoundError("lambda_function.py not found in lambda_build/")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(function_path, "lambda_function.py")

    return zip_path


def update_lambda(zip_path):
    """Upload zip to Lambda"""
    client = boto3.client('lambda', region_name=AWS_REGION)

    with open(zip_path, 'rb') as f:
        response = client.update_function_code(
            FunctionName=LAMBDA_NAME,
            ZipFile=f.read(),
            Publish=True
        )

    return response


def main():
    print("Zipping Lambda code...")
    zip_path = zip_lambda()

    print("Uploading to AWS Lambda...")
    response = update_lambda(zip_path)

    print("\n=== Lambda Updated Successfully ===")
    print("Function:", response["FunctionName"])
    print("Last Modified:", response["LastModified"])
    print("Version:", response["Version"])
    print("State:", response.get("State", "N/A"))


if __name__ == "__main__":
    main()
