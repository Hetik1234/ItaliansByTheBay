import boto3
import datetime
from decimal import Decimal
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)

def get_metric_sum(metric_name, hours=24):
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(hours=hours)

    response = cloudwatch.get_metric_statistics(
        Namespace="ItaliansByTheBay/Orders",
        MetricName=metric_name,
        StartTime=start,
        EndTime=end,
        Period=3600,  # 1-hour buckets
        Statistics=["Sum"]
    )

    datapoints = response.get("Datapoints", [])

    total = sum(dp["Sum"] for dp in datapoints)
    return round(total, 2)


def get_peak_hour():
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(hours=24)

    response = cloudwatch.get_metric_statistics(
        Namespace="ItaliansByTheBay/Orders",
        MetricName="OrdersCount",
        StartTime=start,
        EndTime=end,
        Period=3600,
        Statistics=["Sum"]
    )

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return "N/A"

    # Find hour with most orders
    peak = max(datapoints, key=lambda x: x["Sum"])
    timestamp = peak["Timestamp"].strftime("%H:00")
    count = int(peak["Sum"])

    return f"{timestamp} — {count} orders"
