"""
utils/scheduling.py
Smart delivery scheduling logic.

Rule: the shop can complete only N deliveries per day (default 2).
When a new order is created, start checking from (order_date + default_delivery_days).
If that date already has N deliveries booked, move to the next day, and so on,
until a date with free capacity is found.
"""

from datetime import timedelta


def get_bookings_for_date(order_model, target_date, exclude_order_id=None):
    """Count how many orders are already scheduled for delivery on target_date."""
    query = order_model.query.filter(order_model.delivery_date == target_date)
    if exclude_order_id:
        query = query.filter(order_model.id != exclude_order_id)
    return query.count()


def find_next_available_delivery_date(order_model, order_date, default_delivery_days,
                                        max_per_day, exclude_order_id=None):
    """
    Starting from order_date + default_delivery_days, find the first date
    that has fewer than max_per_day deliveries already booked.
    """
    candidate = order_date + timedelta(days=default_delivery_days)
    # safety cap to avoid infinite loops (1 year)
    for _ in range(365):
        booked = get_bookings_for_date(order_model, candidate, exclude_order_id)
        if booked < max_per_day:
            return candidate
        candidate += timedelta(days=1)
    return candidate


def get_calendar_availability(order_model, start_date, end_date, max_per_day):
    """
    Return a dict of {date_iso: {"booked": n, "available": bool}} for the
    given date range, used to render the delivery calendar.
    """
    from datetime import date as date_cls
    result = {}
    current = start_date
    while current <= end_date:
        booked = get_bookings_for_date(order_model, current)
        result[current.isoformat()] = {
            "booked": booked,
            "capacity": max_per_day,
            "available": booked < max_per_day,
        }
        current += timedelta(days=1)
    return result
