# Tailoring Order Management System (Flask)

## Setup

```bash
cd tailoring_app
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

**Default login:** `admin` / `admin123` — change this immediately from Settings → Admin Login.

## Notes

- Database file is created automatically at `database/tailoring.db` on first run.
- Uploaded images (logo, design, fabric) are stored in `static/uploads/`.
- No business logo was attached to the build request, so a placeholder theme
  (brown/gold) is used. Upload your logo from **Settings** — it will then
  appear on the login page, dashboard, navbar, invoice, and browser favicon.
- Smart delivery scheduling: new orders auto-schedule to the next date with
  free capacity, starting from Order Date + Default Delivery Days
  (both configurable in Settings).
- Reminders (3-day-in-progress, day-before-delivery, delivery-day, overdue)
  are recalculated whenever the dashboard or an order detail page loads.
