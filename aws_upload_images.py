import boto3
import os

BUCKET = "italians-by-the-bay-media"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)

def upload_folder(local_folder, s3_folder):
    for root, dirs, files in os.walk(local_folder):
        for filename in files:
            local_path = os.path.join(root, filename)
            s3_path = f"{s3_folder}/{filename}"

            print(f"Uploading {local_path} → {s3_path}")

            s3.upload_file(
                Filename=local_path,
                Bucket=BUCKET,
                Key=s3_path,
                ExtraArgs={"ContentType": "image/jpeg"}
            )

# Upload menu images
upload_folder("images/menu", "menu_images")

# Upload category images
upload_folder("images/categories", "category_images")

print("\nUpload complete!")
