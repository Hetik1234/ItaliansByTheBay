import boto3
import os
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = "italians-by-the-bay-media"

def get_client(service):
    return boto3.client(service, region_name=AWS_REGION)

def create_s3_bucket():
    print("\n===============================")
    print("  Creating S3 Bucket Programmatically")
    print("===============================\n")

    s3 = get_client("s3")

    # 1) Check if bucket already exists
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' already exists ✔")
    except ClientError:
        try:
            if AWS_REGION == "us-east-1":
                s3.create_bucket(Bucket=BUCKET_NAME)
            else:
                s3.create_bucket(
                    Bucket=BUCKET_NAME,
                    CreateBucketConfiguration={
                        "LocationConstraint": AWS_REGION
                    }
                )
            print(f"Bucket '{BUCKET_NAME}' created ✔")
        except Exception as e:
            print("ERROR creating bucket:", e)
            return False

    # 2) Create media folders
    try:
        s3.put_object(Bucket=BUCKET_NAME, Key="menu_images/")
        s3.put_object(Bucket=BUCKET_NAME, Key="category_images/")
        print("Created 'menu_images/' and 'category_images/' ✔")
    except Exception as e:
        print("ERROR creating folders:", e)

    # 3) Upload test file
    try:
        with open("test_upload.txt", "w") as f:
            f.write("This is a test file uploaded via boto3.")

        s3.upload_file("test_upload.txt", BUCKET_NAME, "test_upload.txt")
        print("Uploaded sample file 'test_upload.txt' ✔")
    except Exception as e:
        print("ERROR uploading sample file:", e)

    return True


if __name__ == "__main__":
    create_s3_bucket()
