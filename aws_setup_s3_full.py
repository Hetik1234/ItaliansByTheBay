import boto3
import os
import json
import mimetypes

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
# Change this number if the bucket name is already taken globally!
BUCKET = "italians-by-the-bay-media-v3" 

s3 = boto3.client("s3", region_name=AWS_REGION)

# ------------------------------
# Create bucket & configure security
# ------------------------------
def create_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
        print(f"✔ Bucket '{BUCKET}' already exists")
    except:
        print(f"Creating bucket '{BUCKET}'...")
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET)
        else:
            s3.create_bucket(
                Bucket=BUCKET,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
            )
        print(f"✔ Bucket created")

    # Disable "Block Public Access" (Required for public bucket policies)
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False
        }
    )
    print("✔ Public access blocks disabled")

    # Apply public-read policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": f"arn:aws:s3:::{BUCKET}/*"
        }]
    }

    s3.put_bucket_policy(
        Bucket=BUCKET,
        Policy=json.dumps(policy)
    )
    print("✔ Public-read policy applied")

    # Apply CORS configuration (Required for browsers to load S3 images)
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'POST', 'PUT', 'HEAD'],
            'AllowedOrigins': ['*'],
            'ExposeHeaders': []
        }]
    }
    
    s3.put_bucket_cors(
        Bucket=BUCKET,
        CORSConfiguration=cors_configuration
    )
    print("✔ CORS configuration applied")


# ------------------------------
# Upload all images
# ------------------------------
def upload_folder(local_folder, s3_prefix):
    """Uploads all images from local_folder to s3://bucket/s3_prefix."""
    print(f"\nUploading {local_folder}/ → s3://{BUCKET}/{s3_prefix}/")

    folder_path = os.path.join(os.getcwd(), local_folder)

    if not os.path.exists(folder_path):
        print(f"✖ Local folder missing: {folder_path}")
        return

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        local_file = os.path.join(folder_path, filename)

        # Normalise filename → replace spaces with underscores
        clean_name = filename.replace(" ", "_")

        s3_key = f"{s3_prefix}/{clean_name}"

        content_type = mimetypes.guess_type(local_file)[0] or "image/jpeg"

        print(f"  Uploading {filename} → {s3_key}")

        s3.upload_file(
            local_file,
            BUCKET,
            s3_key,
            ExtraArgs={"ContentType": content_type}
        )

    print("✔ Upload complete")


# ------------------------------
# Print final URLs
# ------------------------------
def print_final_urls(prefix):
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    print(f"\n==== S3 URLs under '{prefix}/' ====")

    for obj in resp.get("Contents", []):
        key = obj["Key"]
        url = f"https://{BUCKET}.s3.amazonaws.com/{key}"
        print(url)


# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    print("\n===============================")
    print("  FULL S3 SETUP SCRIPT STARTED")
    print("===============================\n")

    create_bucket()

    upload_folder("images/menu", "menu_images")
    upload_folder("images/categories", "category_images")

    print_final_urls("menu_images")
    print_final_urls("category_images")

    print("\nAll done! 🚀")