"""
app.py
Application entry point for the Tailoring Order Management System.

Run with:
    python app.py
Then open http://127.0.0.1:5000
Default login: admin / admin123  (change this immediately in Settings)
"""

import os
from flask import Flask
from models import db, Admin, Settings

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        BASE_DIR, "database", "tailoring.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload cap

    db.init_app(app)

    from routes import bp as main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    """Create a default admin account and settings row if none exist yet."""
    if not Admin.query.first():
        admin = Admin(username="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    Settings.get()  # ensures a settings row exists

    db.session.commit()


app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
