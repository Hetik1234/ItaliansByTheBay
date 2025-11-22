echo "Paste AWS_ACCESS_KEY_ID:"
read key
echo "Paste AWS_SECRET_ACCESS_KEY:"
read secret
echo "Paste AWS_SESSION_TOKEN:"
read token

export AWS_ACCESS_KEY_ID="$key"
export AWS_SECRET_ACCESS_KEY="$secret"
export AWS_SESSION_TOKEN="$token"

echo "Credentials updated!"
