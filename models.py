"""
models.py
Database models for the Tailoring Order Management System.
Uses SQLAlchemy ORM with SQLite as the backend.
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Admin (single shop owner login)
# ---------------------------------------------------------------------------
class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), nullable=False, index=True)
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="customer", lazy=True,
                              cascade="all, delete-orphan")

    @property
    def total_orders(self):
        return len(self.orders)

    @property
    def is_repeat_customer(self):
        return self.total_orders > 1

    @property
    def total_paid(self):
        total = 0
        for o in self.orders:
            for p in o.payments:
                total += p.amount
        return total


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
STATUS_STEPS = [
    "Order Received",
    "Measurement Taken",
    "Cutting",
    "Stitching",
    "Trial",
    "Ready",
    "Delivered",
]

DRESS_CATEGORIES = [
    "Blouse", "Saree Blouse", "Chudidar", "Shirt", "Pant", "Coat",
    "Kurti", "Lehenga", "Kids Dress", "School Uniform", "Alteration",
    "Custom Dress",
]


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False, index=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    order_date = db.Column(db.Date, default=date.today, nullable=False)
    dress_type = db.Column(db.String(80), nullable=False)
    custom_dress_type = db.Column(db.String(120))
    quantity = db.Column(db.Integer, default=1)

    fabric_details = db.Column(db.Text)
    design_notes = db.Column(db.Text)
    special_instructions = db.Column(db.Text)

    trial_date = db.Column(db.Date)
    delivery_date = db.Column(db.Date, nullable=False)

    design_image = db.Column(db.String(255))
    fabric_image = db.Column(db.String(255))

    status = db.Column(db.String(30), default=STATUS_STEPS[0], nullable=False)

    total_amount = db.Column(db.Float, default=0.0)
    stitching_charge = db.Column(db.Float, default=0.0)
    lining_charge = db.Column(db.Float, default=0.0)

    manual_override = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    measurements = db.relationship("OrderMeasurement", backref="order",
                                    uselist=False, cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="order", lazy=True,
                                cascade="all, delete-orphan")
    reminders = db.relationship("Reminder", backref="order", lazy=True,
                                 cascade="all, delete-orphan")

    @property
    def display_dress_type(self):
        if self.dress_type == "Custom Dress" and self.custom_dress_type:
            return self.custom_dress_type
        return self.dress_type

    @property
    def advance_paid(self):
        return sum(p.amount for p in self.payments)

    @property
    def balance(self):
        return round((self.total_amount or 0) - self.advance_paid, 2)

    @property
    def payment_status(self):
        if self.advance_paid <= 0:
            return "Pending"
        if self.balance <= 0:
            return "Paid"
        return "Partial"

    @property
    def progress_percent(self):
        try:
            idx = STATUS_STEPS.index(self.status)
        except ValueError:
            idx = 0
        return int(((idx + 1) / len(STATUS_STEPS)) * 100)

    @property
    def is_overdue(self):
        return self.status != "Delivered" and self.delivery_date < date.today()

    @property
    def days_in_progress(self):
        return (date.today() - self.order_date).days


class OrderMeasurement(db.Model):
    __tablename__ = "order_measurements"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    shoulder = db.Column(db.Float)
    arm_hole = db.Column(db.Float)
    chest = db.Column(db.Float)
    upper_chest = db.Column(db.Float)
    under_bust = db.Column(db.Float)
    waist = db.Column(db.Float)          # Waist Round
    waist_length = db.Column(db.Float)
    natural_waist = db.Column(db.Float)
    hip = db.Column(db.Float)            # Seat
    waist_to_knee = db.Column(db.Float)
    waist_to_ankle = db.Column(db.Float)
    waist_to_calf = db.Column(db.Float)
    length = db.Column(db.Float)         # Other/overall length
    kurti_length = db.Column(db.Float)
    pant_length = db.Column(db.Float)
    leg_round = db.Column(db.Float)
    sleeve_length = db.Column(db.Float)
    sleeve_round = db.Column(db.Float)
    front_neck = db.Column(db.Float)
    back_neck = db.Column(db.Float)
    neck = db.Column(db.Float)           # Neck Round
    extra_notes = db.Column(db.Text)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    method = db.Column(db.String(40), default="Cash")
    note = db.Column(db.String(255))


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------
class Reminder(db.Model):
    __tablename__ = "reminders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    reminder_type = db.Column(db.String(40))  # progress, pre_delivery, delivery_day, overdue
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# Settings (single row table)
# ---------------------------------------------------------------------------
class Settings(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(120), default="My Tailoring Shop")
    address = db.Column(db.Text, default="")
    mobile_number = db.Column(db.String(20), default="")
    whatsapp_number = db.Column(db.String(20), default="")
    gst_number = db.Column(db.String(40), default="")
    default_delivery_days = db.Column(db.Integer, default=5)
    max_deliveries_per_day = db.Column(db.Integer, default=2)
    logo_path = db.Column(db.String(255), default="")

    @staticmethod
    def get():
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings
