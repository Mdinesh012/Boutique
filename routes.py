"""
routes.py
All view functions / routes for the Tailoring Order Management System.
"""

import os
import uuid
from functools import wraps
from datetime import date, datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, jsonify, current_app, send_from_directory
)
from werkzeug.utils import secure_filename

from models import (
    db, Admin, Customer, Order, OrderMeasurement, Payment, Reminder, Settings,
    STATUS_STEPS, DRESS_CATEGORIES
)
from utils.scheduling import find_next_available_delivery_date, get_calendar_availability
from utils.reminders import sync_all_reminders, sync_reminders_for_order

bp = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return wrapper


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(path)
    return filename


def parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@bp.context_processor
def inject_globals():
    return {
        "settings": Settings.get(),
        "STATUS_STEPS": STATUS_STEPS,
        "DRESS_CATEGORIES": DRESS_CATEGORIES,
        "today": date.today(),
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            return redirect(url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@bp.route("/")
@login_required
def dashboard():
    sync_all_reminders(db, Reminder, Order)

    all_orders = Order.query.all()
    total_orders = len(all_orders)
    new_orders = sum(1 for o in all_orders if o.status == "Order Received")
    in_progress = sum(1 for o in all_orders if o.status in
                       ("Measurement Taken", "Cutting", "Stitching", "Trial"))
    ready = sum(1 for o in all_orders if o.status == "Ready")
    delivered = sum(1 for o in all_orders if o.status == "Delivered")
    overdue = sum(1 for o in all_orders if o.is_overdue)

    today = date.today()
    todays_income = sum(
        p.amount for o in all_orders for p in o.payments if p.payment_date == today
    )
    month_start = today.replace(day=1)
    monthly_income = sum(
        p.amount for o in all_orders for p in o.payments if p.payment_date >= month_start
    )
    pending_payments = sum(o.balance for o in all_orders if o.balance > 0)

    upcoming_deliveries = (
        Order.query.filter(Order.status != "Delivered",
                            Order.delivery_date >= today)
        .order_by(Order.delivery_date.asc()).limit(8).all()
    )
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    todays_reminders = (
        Reminder.query.filter(Reminder.is_read == False)  # noqa: E712
        .order_by(Reminder.created_at.desc()).limit(15).all()
    )

    return render_template(
        "dashboard.html",
        total_orders=total_orders, new_orders=new_orders, in_progress=in_progress,
        ready=ready, delivered=delivered, overdue=overdue,
        todays_income=todays_income, monthly_income=monthly_income,
        pending_payments=pending_payments,
        upcoming_deliveries=upcoming_deliveries, recent_orders=recent_orders,
        todays_reminders=todays_reminders,
    )


@bp.route("/reminders/<int:reminder_id>/read", methods=["POST"])
@login_required
def mark_reminder_read(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.is_read = True
    db.session.commit()
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@bp.route("/customers")
@login_required
def customers_list():
    q = request.args.get("q", "").strip()
    query = Customer.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Customer.name.ilike(like), Customer.mobile.ilike(like)))
    customers = query.order_by(Customer.name.asc()).all()
    return render_template("customers.html", customers=customers, q=q)


@bp.route("/customers/add", methods=["GET", "POST"])
@login_required
def customer_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        if not name or not mobile:
            flash("Name and mobile number are required.", "danger")
            return render_template("customer_form.html", customer=None)
        customer = Customer(
            name=name, mobile=mobile,
            address=request.form.get("address", "").strip(),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(customer)
        db.session.commit()
        flash("Customer added successfully.", "success")
        return redirect(url_for("main.customers_list"))
    return render_template("customer_form.html", customer=None)


@bp.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def customer_edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == "POST":
        customer.name = request.form.get("name", "").strip()
        customer.mobile = request.form.get("mobile", "").strip()
        customer.address = request.form.get("address", "").strip()
        customer.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Customer updated.", "success")
        return redirect(url_for("main.customers_list"))
    return render_template("customer_form.html", customer=customer)


@bp.route("/customers/<int:customer_id>/delete", methods=["POST"])
@login_required
def customer_delete(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer deleted.", "info")
    return redirect(url_for("main.customers_list"))


@bp.route("/customers/<int:customer_id>")
@login_required
def customer_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    orders = sorted(customer.orders, key=lambda o: o.order_date, reverse=True)
    return render_template("customer_detail.html", customer=customer, orders=orders)
# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def generate_order_number():
    today_str = date.today().strftime("%Y%m%d")
    count_today = Order.query.filter(
        db.func.date(Order.created_at) == date.today()
    ).count()
    return f"ORD-{today_str}-{count_today + 1:03d}"


@bp.route("/orders")
@login_required
def orders_list():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    sort_by = request.args.get("sort", "delivery_date")

    query = Order.query.join(Customer)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Customer.name.ilike(like),
            Customer.mobile.ilike(like),
            Order.order_number.ilike(like),
        ))
    if status_filter == "Overdue":
        query = query.filter(Order.delivery_date < date.today(), Order.status != "Delivered")
    elif status_filter:
        query = query.filter(Order.status == status_filter)

    if sort_by == "order_date":
        query = query.order_by(Order.order_date.desc())
    elif sort_by == "customer_name":
        query = query.order_by(Customer.name.asc())
    else:
        query = query.order_by(Order.delivery_date.asc())

    orders = query.all()
    return render_template(
        "orders.html", orders=orders, q=q, status_filter=status_filter, sort_by=sort_by
    )


@bp.route("/orders/add", methods=["GET", "POST"])
@login_required
def order_add():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    settings = Settings.get()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        new_customer_name = request.form.get("new_customer_name", "").strip()
        new_customer_mobile = request.form.get("new_customer_mobile", "").strip()

        if not customer_id and new_customer_name and new_customer_mobile:
            customer = Customer(name=new_customer_name, mobile=new_customer_mobile,
                                 address=request.form.get("new_customer_address", ""))
            db.session.add(customer)
            db.session.flush()
            customer_id = customer.id

        if not customer_id:
            flash("Please select or create a customer.", "danger")
            return render_template("order_form.html", order=None, customers=customers,
                                    default_delivery_days=settings.default_delivery_days)

        order_date_val = parse_date(request.form.get("order_date"), date.today())
        dress_type = request.form.get("dress_type", "")
        custom_dress_type = request.form.get("custom_dress_type", "").strip()
        manual_delivery = parse_date(request.form.get("delivery_date"))
        manual_override = bool(manual_delivery)

        if manual_delivery:
            delivery_date_val = manual_delivery
        else:
            delivery_date_val = find_next_available_delivery_date(
                Order, order_date_val, settings.default_delivery_days,
                settings.max_deliveries_per_day,
            )

        order = Order(
            order_number=generate_order_number(),
            customer_id=customer_id,
            order_date=order_date_val,
            dress_type=dress_type,
            custom_dress_type=custom_dress_type if dress_type == "Custom Dress" else None,
            quantity=int(request.form.get("quantity") or 1),
            fabric_details=request.form.get("fabric_details", ""),
            design_notes=request.form.get("design_notes", ""),
            special_instructions=request.form.get("special_instructions", ""),
            trial_date=parse_date(request.form.get("trial_date")),
            delivery_date=delivery_date_val,
            total_amount=parse_float(request.form.get("total_amount"), 0.0),
            manual_override=manual_override,
        )

        design_file = request.files.get("design_image")
        fabric_file = request.files.get("fabric_image")
        order.design_image = save_upload(design_file)
        order.fabric_image = save_upload(fabric_file)

        db.session.add(order)
        db.session.flush()

        measurement = OrderMeasurement(
            order_id=order.id,
            chest=parse_float(request.form.get("chest"), None) or None,
            waist=parse_float(request.form.get("waist"), None) or None,
            hip=parse_float(request.form.get("hip"), None) or None,
            shoulder=parse_float(request.form.get("shoulder"), None) or None,
            sleeve_length=parse_float(request.form.get("sleeve_length"), None) or None,
            length=parse_float(request.form.get("length"), None) or None,
            neck=parse_float(request.form.get("neck"), None) or None,
            arm_hole=parse_float(request.form.get("arm_hole"), None) or None,
            extra_notes=request.form.get("measurement_notes", ""),
        )
        db.session.add(measurement)

        advance = parse_float(request.form.get("advance_paid"), 0.0)
        if advance > 0:
            db.session.add(Payment(order_id=order.id, amount=advance, method="Cash",
                                    note="Advance at order creation"))

        db.session.commit()
        flash(f"Order {order.order_number} created. Delivery scheduled for "
              f"{delivery_date_val.strftime('%d %b %Y')}.", "success")
        return redirect(url_for("main.order_detail", order_id=order.id))

    return render_template("order_form.html", order=None, customers=customers,
                            default_delivery_days=settings.default_delivery_days)


@bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    sync_reminders_for_order(db, Reminder, order)
    return render_template("order_detail.html", order=order)


@bp.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def order_edit(order_id):
    order = Order.query.get_or_404(order_id)
    customers = Customer.query.order_by(Customer.name.asc()).all()

    if request.method == "POST":
        order.customer_id = request.form.get("customer_id", order.customer_id)
        order.order_date = parse_date(request.form.get("order_date"), order.order_date)
        order.dress_type = request.form.get("dress_type", order.dress_type)
        order.custom_dress_type = request.form.get("custom_dress_type", "").strip() or None
        order.quantity = int(request.form.get("quantity") or order.quantity)
        order.fabric_details = request.form.get("fabric_details", "")
        order.design_notes = request.form.get("design_notes", "")
        order.special_instructions = request.form.get("special_instructions", "")
        order.trial_date = parse_date(request.form.get("trial_date"))

        manual_delivery = parse_date(request.form.get("delivery_date"))
        if manual_delivery:
            order.delivery_date = manual_delivery
            order.manual_override = True

        order.total_amount = parse_float(request.form.get("total_amount"), order.total_amount)

        design_file = request.files.get("design_image")
        fabric_file = request.files.get("fabric_image")
        new_design = save_upload(design_file)
        new_fabric = save_upload(fabric_file)
        if new_design:
            order.design_image = new_design
        if new_fabric:
            order.fabric_image = new_fabric

        if not order.measurements:
            order.measurements = OrderMeasurement(order_id=order.id)
        m = order.measurements
        m.chest = parse_float(request.form.get("chest"), None) or None
        m.waist = parse_float(request.form.get("waist"), None) or None
        m.hip = parse_float(request.form.get("hip"), None) or None
        m.shoulder = parse_float(request.form.get("shoulder"), None) or None
        m.sleeve_length = parse_float(request.form.get("sleeve_length"), None) or None
        m.length = parse_float(request.form.get("length"), None) or None
        m.neck = parse_float(request.form.get("neck"), None) or None
        m.arm_hole = parse_float(request.form.get("arm_hole"), None) or None
        m.extra_notes = request.form.get("measurement_notes", "")

        db.session.commit()
        flash("Order updated.", "success")
        return redirect(url_for("main.order_detail", order_id=order.id))

    return render_template("order_form.html", order=order, customers=customers,
                            default_delivery_days=Settings.get().default_delivery_days)


@bp.route("/orders/<int:order_id>/delete", methods=["POST"])
@login_required
def order_delete(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash("Order deleted.", "info")
    return redirect(url_for("main.orders_list"))


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
def order_update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in STATUS_STEPS:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.order_number} marked as {new_status}.", "success")
    return redirect(url_for("main.order_detail", order_id=order.id))


@bp.route("/orders/<int:order_id>/payment", methods=["POST"])
@login_required
def order_add_payment(order_id):
    order = Order.query.get_or_404(order_id)
    amount = parse_float(request.form.get("amount"), 0.0)
    method = request.form.get("method", "Cash")
    note = request.form.get("note", "")
    if amount > 0:
        db.session.add(Payment(order_id=order.id, amount=amount, method=method, note=note))
        db.session.commit()
        flash(f"Payment of Rs.{amount:.2f} recorded.", "success")
    else:
        flash("Enter a valid payment amount.", "danger")
    return redirect(url_for("main.order_detail", order_id=order.id))


# ---------------------------------------------------------------------------
# Delivery calendar (JSON API used by dashboard / order form)
# ---------------------------------------------------------------------------
@bp.route("/api/calendar")
@login_required
def api_calendar():
    settings = Settings.get()
    start = parse_date(request.args.get("start"), date.today())
    end = start + timedelta(days=59)
    data = get_calendar_availability(Order, start, end, settings.max_deliveries_per_day)
    return jsonify(data)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
@bp.route("/reports")
@login_required
def reports():
    return render_template("reports.html")


@bp.route("/api/reports/data")
@login_required
def api_reports_data():
    period = request.args.get("period", "monthly")
    today = date.today()

    if period == "daily":
        start = today
    elif period == "weekly":
        start = today - timedelta(days=today.weekday())
    elif period == "yearly":
        start = today.replace(month=1, day=1)
    else:
        start = today.replace(day=1)

    orders_in_range = Order.query.filter(Order.order_date >= start).all()
    all_orders = Order.query.all()

    income = sum(p.amount for o in orders_in_range for p in o.payments
                 if p.payment_date >= start)

    income_by_day = {}
    for o in orders_in_range:
        for p in o.payments:
            if p.payment_date >= start:
                key = p.payment_date.isoformat()
                income_by_day[key] = income_by_day.get(key, 0) + p.amount
    labels = sorted(income_by_day.keys())
    values = [income_by_day[d] for d in labels]

    status_counts = {}
    for o in all_orders:
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    return jsonify({
        "period": period,
        "total_income": income,
        "total_orders": len(orders_in_range),
        "completed_orders": sum(1 for o in orders_in_range if o.status == "Delivered"),
        "pending_orders": sum(1 for o in orders_in_range if o.status != "Delivered"),
        "overdue_orders": sum(1 for o in all_orders if o.is_overdue),
        "pending_payments": sum(o.balance for o in all_orders if o.balance > 0),
        "chart_labels": labels,
        "chart_values": values,
        "status_labels": list(status_counts.keys()),
        "status_values": list(status_counts.values()),
    })


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
@bp.route("/orders/<int:order_id>/invoice")
@login_required
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("invoice.html", order=order)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    settings = Settings.get()
    if request.method == "POST":
        settings.shop_name = request.form.get("shop_name", settings.shop_name)
        settings.address = request.form.get("address", settings.address)
        settings.mobile_number = request.form.get("mobile_number", settings.mobile_number)
        settings.whatsapp_number = request.form.get("whatsapp_number", settings.whatsapp_number)
        settings.gst_number = request.form.get("gst_number", settings.gst_number)
        settings.default_delivery_days = int(request.form.get(
            "default_delivery_days") or settings.default_delivery_days)
        settings.max_deliveries_per_day = int(request.form.get(
            "max_deliveries_per_day") or settings.max_deliveries_per_day)

        logo_file = request.files.get("logo")
        new_logo = save_upload(logo_file)
        if new_logo:
            settings.logo_path = new_logo

        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("password", "").strip()
        if new_username or new_password:
            admin = Admin.query.get(session["admin_id"])
            if new_username:
                admin.username = new_username
                session["admin_username"] = new_username
            if new_password:
                admin.set_password(new_password)

        db.session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("main.settings_page"))

    return render_template("settings.html", settings=settings)
