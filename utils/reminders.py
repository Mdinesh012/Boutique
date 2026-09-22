"""
utils/reminders.py
Automatic reminder generation, run on each dashboard load / order view.

Rules:
- Day 3 of an order still not Delivered -> "in progress for 3 days" reminder
- One day before delivery_date -> "Delivery is tomorrow"
- On delivery_date (not yet delivered) -> "Deliver this order today"
- After delivery_date and still not Delivered -> mark OVERDUE reminder
"""

from datetime import date, timedelta


def sync_reminders_for_order(db, Reminder, order):
    today = date.today()

    def has_reminder(rtype):
        return any(r.reminder_type == rtype for r in order.reminders)

    if order.status == "Delivered":
        return

    # Day 3 in progress
    if order.days_in_progress >= 3 and not has_reminder("progress_day3"):
        db.session.add(Reminder(
            order_id=order.id,
            message=f"Order {order.order_number} has been in progress for 3 days.",
            reminder_type="progress_day3",
        ))

    # One day before delivery
    if order.delivery_date - timedelta(days=1) == today and not has_reminder("pre_delivery"):
        db.session.add(Reminder(
            order_id=order.id,
            message=f"Delivery for order {order.order_number} is tomorrow.",
            reminder_type="pre_delivery",
        ))

    # Delivery day
    if order.delivery_date == today and not has_reminder("delivery_day"):
        db.session.add(Reminder(
            order_id=order.id,
            message=f"Deliver order {order.order_number} today.",
            reminder_type="delivery_day",
        ))

    # Overdue
    if order.delivery_date < today and not has_reminder("overdue"):
        db.session.add(Reminder(
            order_id=order.id,
            message=f"Order {order.order_number} is OVERDUE.",
            reminder_type="overdue",
        ))

    db.session.commit()


def sync_all_reminders(db, Reminder, Order):
    orders = Order.query.filter(Order.status != "Delivered").all()
    for order in orders:
        sync_reminders_for_order(db, Reminder, order)
