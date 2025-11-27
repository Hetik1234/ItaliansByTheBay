import boto3
import json
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)

dashboard_name = "ItaliansByTheBayDashboard"

widgets = [
    # ----- Orders Count ------
    {
        "type": "metric",
        "width": 6,
        "height": 6,
        "properties": {
            "metrics": [
                ["ItaliansByTheBay/Orders", "OrdersCount"]
            ],
            "period": 300,
            "stat": "Sum",
            "region": AWS_REGION,
            "title": "Total Orders (5 min)"
        }
    },

    # ----- Revenue ------
    {
        "type": "metric",
        "width": 6,
        "height": 6,
        "properties": {
            "metrics": [
                ["ItaliansByTheBay/Orders", "Revenue"]
            ],
            "period": 300,
            "stat": "Average",
            "region": AWS_REGION,
            "title": "Average Revenue (5 min)"
        }
    },

    # ----- SQS Queue Depth ------
    {
        "type": "metric",
        "width": 6,
        "height": 6,
        "properties": {
            "metrics": [
                ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", "italians-order-queue"]
            ],
            "period": 60,
            "stat": "Average",
            "region": AWS_REGION,
            "title": "SQS Queue Depth"
        }
    },

    # ----- Lambda Invocation Count ------
    {
        "type": "metric",
        "width": 6,
        "height": 6,
        "properties": {
            "metrics": [
                ["AWS/Lambda", "Invocations", "FunctionName", "orderPlacedHandler"]
            ],
            "period": 300,
            "stat": "Sum",
            "region": AWS_REGION,
            "title": "Lambda Invocations"
        }
    }
]

dashboard_body = json.dumps({"widgets": widgets})

cloudwatch.put_dashboard(
    DashboardName=dashboard_name,
    DashboardBody=dashboard_body
)

print("Dashboard created successfully:", dashboard_name)
