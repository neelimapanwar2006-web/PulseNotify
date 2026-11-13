import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction
from .models import NotificationLog, PriceAlert

@shared_task
def check_prices():
    active_alerts = PriceAlert.objects.filter(status=PriceAlert.Status.ACTIVE)
    routes = active_alerts.values_list("origin", "destination").distinct()

    for origin, destination in routes:
        route = f"{origin}-{destination}"
        try:
            response = requests.get(
                f"{settings.PRICE_FEED_BASE_URL}/api/flights/price/",
                params={"route": route},
                timeout=10,
            )
            response.raise_for_status()
            current_price = response.json().get("price")
        except (requests.RequestException, ValueError, TypeError):
            continue

        matching_alerts = active_alerts.filter(origin=origin, destination=destination)
        for alert in matching_alerts:
            if current_price is not None and current_price <= float(alert.threshold_price):
                send_notification.delay(alert.id, current_price)


@shared_task
def send_notification(alert_id, triggered_price):
    # Re-check status to reduce duplicate notifications if tasks overlap.
    with transaction.atomic():
        try:
            alert = PriceAlert.objects.select_for_update().get(
                id=alert_id, status=PriceAlert.Status.ACTIVE
            )
        except PriceAlert.DoesNotExist:
            return "Alert no longer active"

        message = (
            f"Price alert triggered! {alert.origin}-{alert.destination} "
            f"is now ₹{triggered_price} - below your threshold of "
            f"₹{alert.threshold_price}"
        )
        NotificationLog.objects.create(
            alert=alert, triggered_price=triggered_price, message=message
        )
        alert.status = PriceAlert.Status.TRIGGERED
        alert.save(update_fields=["status"])
    return "Notification created"
