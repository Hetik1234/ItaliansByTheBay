import boto3, os
from django.shortcuts import render
from django.contrib.auth.models import User
from decimal import Decimal

def dynamo_dashboard(request):
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    TABLE = os.getenv("DDB_TABLE_NAME", "OrderAnalytics")

    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = ddb.Table(TABLE)

    resp = table.scan()
    items = resp.get("Items", [])
    
    items = sorted(
    items,
    key=lambda x: x.get("created_at", ""),
    reverse=True
    )
    # Normalize values and add username
    for item in items:

        # convert total
        if "total" in item:
            try:
                if isinstance(item["total"], Decimal):
                    item["total"] = float(item["total"])
                else:
                    item["total"] = float(str(item["total"]))
            except:
                item["total"] = 0.0

        # ---- FIX USERNAME HERE ----
        raw_uid = item.get("user_id")

        # normalize uid to int
        try:
            if isinstance(raw_uid, Decimal):
                uid = int(raw_uid)
            else:
                uid = int(str(raw_uid))  # handles "1", 1, " 1 "
        except:
            uid = None

        # lookup username
        if uid:
            try:
                item["username"] = User.objects.get(id=uid).username
            except User.DoesNotExist:
                item["username"] = "Unknown"
        else:
            item["username"] = "Unknown"

    return render(request, "orders/dynamo_dashboard.html", {
        "orders": items,
        "count": len(items),
        "total_revenue": sum(float(o.get("total", 0)) for o in items)
    })
