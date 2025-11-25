import boto3

ssm = boto3.client("ssm", region_name="us-east-1")

def put(name, value):
    ssm.put_parameter(
        Name=name,
        Value=value,
        Type="SecureString",
        Overwrite=True
    )
    print(f"✔ Stored SSM parameter: {name}")

# Store secrets
put("/italians/SECRET_KEY", "Hetik12345678")
put("/italians/EMAIL_HOST_USER", "hetikchandaria67@gmail.com")
put("/italians/EMAIL_HOST_PASSWORD", "bbyyorxkamooifci")
put("/italians/DEFAULT_FROM_EMAIL", "no-reply@italians_by_the_bay.com")

print("\nAll parameters stored successfully.")
