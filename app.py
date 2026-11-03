import os
import secrets
from datetime import datetime
from functools import wraps

# Load local environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, make_response
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

from database import get_connection
from analysis import analyze_accidents, get_accident_summary
from init_db import init_database

app = Flask(__name__)

# Production reverse proxy compatibility (Railway SSL/TLS termination)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Secret key configured via environment variable
app.secret_key = (
    os.environ.get("FLASK_SECRET_KEY")
    or os.environ.get("SECRET_KEY")
    or secrets.token_hex(32)
)

# Auto-initialize database tables (users table) on application start
try:
    init_database()
except Exception as init_err:
    app.logger.warning(f"Database initialization note: {init_err}")


# =====================================================
# SECURITY & AUTHENTICATION UTILITIES
# =====================================================
@app.context_processor
def inject_globals():
    """Injects CSRF token and authenticated user info into all templates."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return {
        "csrf_token": session["csrf_token"],
        "current_user": session.get("username")
    }


def validate_csrf():
    """Validates the submitted CSRF token against the session token."""
    token = request.form.get("csrf_token")
    session_token = session.get("csrf_token")
    if not token or not session_token or not secrets.compare_digest(token, session_token):
        return False
    return True


def login_required(f):
    """Decorator ensuring routes require authentication and set cache-control."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access the system.", "error")
            return redirect(url_for("login"))

        response = make_response(f(*args, **kwargs))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return decorated_function


# =====================================================
# AUTHENTICATION ROUTES
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    """Sign-in route with secure password hashing and session management."""
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf():
            flash("Security verification failed. Please try again.", "error")
            return render_template("login.html"), 400

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html"), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = %s LIMIT 1",
                (username,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["csrf_token"] = secrets.token_hex(32)
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for("home"))
            else:
                flash("Invalid username or password.", "error")
                return render_template("login.html"), 401

        except Exception as error:
            app.logger.exception("Login database error")
            flash("Database error during sign in. Check database connection.", "error")
            return render_template("login.html"), 500

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration route allowing anyone to create an account."""
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf():
            flash("Security verification failed. Please try again.", "error")
            return render_template("signup.html"), 400

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # 1. Validate that all fields are filled in
        if not username or not password or not confirm_password:
            flash("Please fill in all fields.", "error")
            return render_template("signup.html"), 400

        # Username length check
        if len(username) < 3 or len(username) > 50:
            flash("Username must be between 3 and 50 characters.", "error")
            return render_template("signup.html"), 400

        # 2. Require a password of at least 8 characters
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("signup.html"), 400

        # 3. Ensure password and confirmation match
        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
            return render_template("signup.html"), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            # 4. Check if username already exists
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s LIMIT 1",
                (username,)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                flash("Username already exists. Please choose another.", "error")
                return render_template("signup.html"), 409

            # 5. Store password securely using Werkzeug password hashing
            pw_hash = generate_password_hash(password)

            # 6. Insert new user into database using parameterized SQL query
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, pw_hash)
            )
            connection.commit()

            # 7. Flash success and redirect to login
            flash("Account created successfully. Please sign in.", "success")
            return redirect(url_for("login"))

        except Exception as error:
            if connection:
                connection.rollback()
            app.logger.exception("Signup database error")
            flash("Database error during account creation. Please try again.", "error")
            return render_template("signup.html"), 500

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("signup.html")


@app.route("/logout", methods=["POST"])
def logout():
    """Secure logout requiring CSRF validation."""
    if not validate_csrf():
        flash("Security verification failed during logout.", "error")
        return redirect(url_for("home"))

    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))


# =====================================================
# DASHBOARD
# =====================================================
@app.route("/")
@login_required
def home():
    """Main dashboard displaying database-backed statistics."""
    summary = get_accident_summary()

    return render_template(
        "index.html",
        total_accidents=summary["total_accidents"],
        most_affected_region=summary["most_affected_region"],
        most_common_vehicle=summary["most_common_vehicle"],
        busiest_hour=summary["busiest_hour"],
        severity_counts=summary["severity_counts"],
        severity_percentages=summary["severity_percentages"]
    )


# =====================================================
# ACCIDENT RECORDS (With Delete Option)
# =====================================================
@app.route("/accidents")
@login_required
def view_accidents():
    """Accident records list ordered by most recent timestamp."""
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                a.accident_id,
                a.accident_datetime,
                l.region,
                l.road_name,
                a.vehicle_type,
                a.severity,
                a.weather,
                a.cause_of_accident
            FROM accidents a
            JOIN locations l
                ON a.location_id = l.location_id
            ORDER BY a.accident_datetime DESC
        """)

        accidents = cursor.fetchall()

        return render_template(
            "accidents.html",
            accidents=accidents
        )

    except Exception as error:
        app.logger.exception("Unable to load accident records")
        return f"Unable to load accident records. Error: {error}", 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/delete-accident/<int:accident_id>", methods=["POST"])
@login_required
def delete_accident(accident_id):
    """Deletes an individual accident record safely with CSRF and validation."""
    if not validate_csrf():
        flash("Security verification failed for deletion.", "error")
        return redirect(url_for("view_accidents"))

    if accident_id <= 0:
        flash("Invalid accident record ID.", "error")
        return redirect(url_for("view_accidents"))

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Verify existence of the record
        cursor.execute("SELECT accident_id FROM accidents WHERE accident_id = %s", (accident_id,))
        record = cursor.fetchone()

        if not record:
            flash(f"Accident record #{accident_id} was not found.", "error")
            return redirect(url_for("view_accidents"))

        # 2. Delete the accident record (foreign key child row)
        cursor.execute("DELETE FROM accidents WHERE accident_id = %s", (accident_id,))
        connection.commit()

        # 3. Refresh analytical charts
        try:
            analyze_accidents()
        except Exception as chart_err:
            app.logger.warning(f"Chart refresh warning: {chart_err}")

        flash(f"Accident record #{accident_id} was deleted successfully.", "success")

    except Exception as error:
        if connection:
            connection.rollback()
        app.logger.exception(f"Error deleting accident record #{accident_id}")
        flash(f"Unable to delete record #{accident_id}. Database error occurred.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("view_accidents"))


# =====================================================
# ANALYSIS PAGE
# =====================================================
@app.route("/analysis")
@login_required
def show_analysis():
    """Generates charts and renders the analysis page."""
    analyze_accidents()
    summary = get_accident_summary()

    return render_template(
        "analysis.html",
        chart_files=[
            "hourly_accidents.png",
            "location_accidents.png",
            "severity_accidents.png",
            "time_period_accidents.png"
        ],
        total_accidents=summary["total_accidents"],
        most_affected_region=summary["most_affected_region"],
        most_common_vehicle=summary["most_common_vehicle"],
        busiest_hour=summary["busiest_hour"],
        severity_counts=summary["severity_counts"],
        severity_percentages=summary["severity_percentages"]
    )


# =====================================================
# ADD ACCIDENT
# =====================================================
@app.route("/add-accident", methods=["POST"])
@login_required
def add_accident():
    """Adds a new accident record with CSRF protection and validation."""
    if not validate_csrf():
        flash("Security token verification failed.", "error")
        return redirect(url_for("home") + "#add-accident")

    accident_datetime = request.form.get("accident_datetime", "").strip()
    region = request.form.get("region", "").strip()
    road_name = request.form.get("road_name", "").strip()
    vehicle_type = request.form.get("vehicle_type", "").strip()
    severity = request.form.get("severity", "").strip()
    weather = request.form.get("weather", "").strip()
    cause_select = request.form.get("cause_of_accident", "").strip()
    other_cause = request.form.get("other_cause", "").strip()

    allowed_vehicles = {"Car", "Bike", "Bus", "Truck", "Auto", "Other"}
    allowed_severities = {"Minor", "Serious", "Fatal"}
    allowed_weather = {"Clear", "Rainy", "Foggy", "Other"}
    allowed_causes = {
        "Rash Driving",
        "Over Speeding",
        "Drunk Driving",
        "Street Light Problem",
        "Poor Road Conditions",
        "Distracted Driving",
        "Traffic Rule Violation",
        "Other"
    }

    if not accident_datetime or not region or not vehicle_type or not severity or not cause_select:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("home") + "#add-accident")

    if cause_select not in allowed_causes:
        flash("Please select a valid cause of accident.", "error")
        return redirect(url_for("home") + "#add-accident")

    if cause_select == "Other":
        if not other_cause:
            flash("Please enter the specific cause of accident for 'Other'.", "error")
            return redirect(url_for("home") + "#add-accident")
        if len(other_cause) > 255:
            flash("Cause of accident is too long (maximum 255 characters).", "error")
            return redirect(url_for("home") + "#add-accident")
        cause_of_accident = other_cause
    else:
        cause_of_accident = cause_select

    try:
        parsed_datetime = datetime.fromisoformat(accident_datetime)
    except ValueError:
        flash("Please enter a valid accident date and time.", "error")
        return redirect(url_for("home") + "#add-accident")

    if parsed_datetime > datetime.now():
        flash("Accident date and time cannot be in the future.", "error")
        return redirect(url_for("home") + "#add-accident")

    if len(region) > 100 or len(road_name) > 150:
        flash("Region or road name is too long.", "error")
        return redirect(url_for("home") + "#add-accident")

    if vehicle_type not in allowed_vehicles:
        flash("Please select a valid vehicle type.", "error")
        return redirect(url_for("home") + "#add-accident")

    if severity not in allowed_severities:
        flash("Please select a valid severity.", "error")
        return redirect(url_for("home") + "#add-accident")

    if weather and weather not in allowed_weather:
        flash("Please select valid weather.", "error")
        return redirect(url_for("home") + "#add-accident")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT location_id FROM locations WHERE region = %s AND road_name <=> %s LIMIT 1",
            (region, road_name or None)
        )

        location = cursor.fetchone()

        if location:
            location_id = location["location_id"]
        else:
            cursor.execute(
                "INSERT INTO locations (region, road_name) VALUES (%s, %s)",
                (region, road_name or None)
            )
            location_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO accidents
                (accident_datetime, location_id, vehicle_type, severity, weather, cause_of_accident)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            parsed_datetime,
            location_id,
            vehicle_type,
            severity,
            weather or None,
            cause_of_accident
        ))

        connection.commit()

        # Refresh analytical charts
        try:
            analyze_accidents()
        except Exception as chart_err:
            app.logger.warning(f"Could not refresh charts immediately: {chart_err}")

        flash("Accident record added successfully!", "success")

    except Exception:
        if connection:
            connection.rollback()
        app.logger.exception("Unable to add accident record")
        flash("Unable to add the record. Database error occurred.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return redirect(url_for("home") + "#add-accident")


# =====================================================
# RUN APPLICATION (Local development & fallback runner)
# In production on Railway, Gunicorn executes `app:app`
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = (
        os.environ.get("FLASK_ENV") == "development"
        or os.environ.get("DEBUG", "False").lower() in ("true", "1")
    )
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
