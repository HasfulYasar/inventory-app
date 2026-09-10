from flask import Flask, request, jsonify, send_from_directory, session, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import psycopg2.errors
import sqlite3
import os
from datetime import datetime, timezone

def utc_now_naive():
    """True UTC wall-clock time, regardless of the DB session's timezone
    setting. Postgres' CURRENT_TIMESTAMP resolves to the session timezone
    (which may be IST on this server), silently storing non-UTC time in a
    plain TIMESTAMP column — this sidesteps that by generating UTC in
    Python and passing it as a parameter."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
CORS(app, supports_credentials=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, "client")

# If DATABASE_URL is set (e.g. on the EC2/production server), we connect to
# that Postgres database exactly as before. If it's NOT set (e.g. running on
# a developer's laptop with nothing configured), we fall back to a local
# SQLite file — no install or setup required, just for quick local testing.
_env_url = os.environ.get("DATABASE_URL")
if _env_url:
    DB_ENGINE = "postgres"
    DATABASE_URL = _env_url
else:
    DB_ENGINE = "sqlite"
    DATABASE_URL = os.path.join(BASE_DIR, "local_dev.db")
    print(f"[dev mode] No DATABASE_URL set — using local SQLite file at {DATABASE_URL}")

# Max size (chars) accepted for a base64 logo data URL — keeps the DB sane.
MAX_LOGO_LEN = 700_000  # ~500KB image

DEFAULT_BOARD_COLOR = "#1a1a2e"
DEFAULT_RATE_COLOR = "#12B76A"
DEFAULT_FONT_SCALE = 1.0
MIN_FONT_SCALE = 0.8
MAX_FONT_SCALE = 5.0
DEFAULT_BOARD_SUBTITLE = "Currency Exchange"
DEFAULT_BOARD_LICENSE = "Perniagaan Perkhidmatan Wang Berlesen"
MAX_TEXT_FIELD_LEN = 120
DEFAULT_PRIMARY_DISPLAY_COUNT = 22
MIN_PRIMARY_DISPLAY_COUNT = 6
MAX_PRIMARY_DISPLAY_COUNT = 60
DEFAULT_SECONDARY_GROUP_SIZE = 10
ALLOWED_SECONDARY_GROUP_SIZES = (5, 10)

PRIMARY_CURRENCIES = [
    "USD","GBP","JPY","EUR","AUD","SGD","HKD","CAD","CHF","NZD",
    "TWD","KRW","INR","THB","CNY","IDR","SAR","MYR","PHP","VND",
    "AED","BND","TRY","RUB"
]

ALL_CURRENCIES = [
    "USD","GBP","JPY","EUR","AUD","SGD","HKD","CAD","CHF","NZD",
    "TWD","KRW","INR","THB","CNY","IDR","SAR","MYR","PHP","VND",
    "AED","BND","TRY","RUB",
    "DKK","SEK","NOK","ZAR","PKR","OMR","JOD","BHD","EGP","QAR",
    "KWD","LKR","BDT","MOP","SCR","IQD","NPR","CZK","KHR"
]

DEFAULT_RATES = {
    "USD":(1,0,0,2),"GBP":(1,0,0,2),"JPY":(100,0,0,2),"EUR":(1,0,0,2),
    "AUD":(1,0,0,2),"SGD":(1,0,0,2),"HKD":(10,0,0,2),"CAD":(1,0,0,2),
    "CHF":(1,0,0,2),"NZD":(1,0,0,2),"TWD":(100,0,0,2),"KRW":(100,0,0,2),
    "INR":(1,0,0,2),"THB":(100,0,0,2),"CNY":(10,0,0,2),"IDR":(100,0,0,2),
    "SAR":(1,0,0,2),"MYR":(1,0,0,2),"PHP":(100,0,0,2),"VND":(100,0,0,2),
    "AED":(1,0,0,2),"BND":(1,0,0,2),"TRY":(1,0,0,2),"RUB":(100,0,0,2),
    "DKK":(10,0,0,2),"SEK":(10,0,0,2),"NOK":(10,0,0,2),"ZAR":(10,0,0,2),
    "PKR":(100,0,0,2),"OMR":(1,0,0,2),"JOD":(1,0,0,2),"BHD":(1,0,0,2),
    "EGP":(10,0,0,2),"QAR":(1,0,0,2),"KWD":(1,0,0,2),"LKR":(100,0,0,2),
    "BDT":(100,0,0,2),"MOP":(10,0,0,2),"SCR":(10,0,0,2),"IQD":(100,0,0,2),
    "NPR":(100,0,0,2),"CZK":(10,0,0,2),"KHR":(1000,0,0,2),
}


class Db:
    """Thin wrapper so existing code that calls db.execute(...).fetchone()/
    .fetchall() and reads row['col'] keeps working unchanged, whether it's
    backed by psycopg2 (Postgres, production) or sqlite3 (local dev)."""
    def __init__(self, conn, engine):
        self.conn = conn
        self.engine = engine

    def execute(self, sql, params=()):
        if self.engine == "postgres":
            sql = sql.replace("?", "%s")
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()


def get_db():
    if "db" not in g:
        if DB_ENGINE == "postgres":
            conn = psycopg2.connect(DATABASE_URL)
        else:
            conn = sqlite3.connect(DATABASE_URL)
            conn.row_factory = sqlite3.Row
        g.db = Db(conn, DB_ENGINE)
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.conn.close()


def init_db():
    with app.app_context():
        db = get_db()
        if DB_ENGINE == "postgres":
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL DEFAULT ''
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS currencies (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 0 REFERENCES users(id),
                    currency TEXT NOT NULL,
                    unit INTEGER NOT NULL DEFAULT 1,
                    buying_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
                    selling_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
                    decimals INTEGER NOT NULL DEFAULT 2,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    sort_order INTEGER NOT NULL DEFAULT 999
                )
            ''')
            # Migrations for existing DBs (Postgres supports IF NOT EXISTS here,
            # unlike SQLite, so no try/except dance is needed)
            for col, defn in [
                ("unit",          "INTEGER NOT NULL DEFAULT 1"),
                ("user_id",       "INTEGER NOT NULL DEFAULT 0"),
                ("sort_order",    "INTEGER NOT NULL DEFAULT 999"),
                ("buy_preorder",  "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("sell_preorder", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("updated_at",    "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                ("currency_name", "TEXT NOT NULL DEFAULT ''"),
                ("currency_flag", "TEXT NOT NULL DEFAULT ''"),
                ("row_color",     "TEXT NOT NULL DEFAULT ''"),
            ]:
                db.execute(f"ALTER TABLE currencies ADD COLUMN IF NOT EXISTS {col} {defn}")
            for col, defn in [
                ("email",        "TEXT NOT NULL DEFAULT ''"),
                ("display_name", "TEXT NOT NULL DEFAULT ''"),
                ("board_color",  f"TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_COLOR}'"),
                ("rate_color",   f"TEXT NOT NULL DEFAULT '{DEFAULT_RATE_COLOR}'"),
                ("logo_data",    "TEXT NOT NULL DEFAULT ''"),
                ("board_name",   "TEXT NOT NULL DEFAULT ''"),
                ("font_scale",   f"DOUBLE PRECISION NOT NULL DEFAULT {DEFAULT_FONT_SCALE}"),
                ("board_subtitle", f"TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_SUBTITLE}'"),
                ("board_license",  f"TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_LICENSE}'"),
                ("board_register_no", "TEXT NOT NULL DEFAULT ''"),
                ("mobile_number",  "TEXT NOT NULL DEFAULT ''"),
                ("primary_display_count", f"INTEGER NOT NULL DEFAULT {DEFAULT_PRIMARY_DISPLAY_COUNT}"),
                ("secondary_group_size", f"INTEGER NOT NULL DEFAULT {DEFAULT_SECONDARY_GROUP_SIZE}"),
            ]:
                db.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {defn}")
        else:
            # SQLite (local dev only): no SERIAL/BOOLEAN keywords, and no
            # "ADD COLUMN IF NOT EXISTS", so we check existing columns first.
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL DEFAULT ''
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS currencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL,
                    unit INTEGER NOT NULL DEFAULT 1,
                    buying_rate REAL NOT NULL DEFAULT 0,
                    selling_rate REAL NOT NULL DEFAULT 0,
                    decimals INTEGER NOT NULL DEFAULT 2,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 999
                )
            ''')

            def existing_columns(table):
                rows = db.execute(f"PRAGMA table_info({table})").fetchall()
                return {r["name"] for r in rows}

            currency_cols = existing_columns("currencies")
            for col, defn in [
                ("unit",          "INTEGER NOT NULL DEFAULT 1"),
                ("user_id",       "INTEGER NOT NULL DEFAULT 0"),
                ("sort_order",    "INTEGER NOT NULL DEFAULT 999"),
                ("buy_preorder",  "BOOLEAN NOT NULL DEFAULT 0"),
                ("sell_preorder", "BOOLEAN NOT NULL DEFAULT 0"),
                ("updated_at",    "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                ("currency_name", "TEXT NOT NULL DEFAULT ''"),
                ("currency_flag", "TEXT NOT NULL DEFAULT ''"),
                ("row_color",     "TEXT NOT NULL DEFAULT ''"),
            ]:
                if col not in currency_cols:
                    db.execute(f"ALTER TABLE currencies ADD COLUMN {col} {defn}")

            user_cols = existing_columns("users")
            for col, defn in [
                ("email",        "TEXT NOT NULL DEFAULT ''"),
                ("display_name", "TEXT NOT NULL DEFAULT ''"),
                ("board_color",  f"TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_COLOR}'"),
                ("rate_color",   f"TEXT NOT NULL DEFAULT '{DEFAULT_RATE_COLOR}'"),
                ("logo_data",    "TEXT NOT NULL DEFAULT ''"),
                ("board_name",   "TEXT NOT NULL DEFAULT ''"),
                ("font_scale",   f"REAL NOT NULL DEFAULT {DEFAULT_FONT_SCALE}"),
                ("board_subtitle", f"TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_SUBTITLE}'"),
                ("board_license",  f"TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_LICENSE}'"),
                ("board_register_no", "TEXT NOT NULL DEFAULT ''"),
                ("mobile_number",  "TEXT NOT NULL DEFAULT ''"),
                ("primary_display_count", f"INTEGER NOT NULL DEFAULT {DEFAULT_PRIMARY_DISPLAY_COUNT}"),
                ("secondary_group_size", f"INTEGER NOT NULL DEFAULT {DEFAULT_SECONDARY_GROUP_SIZE}"),
            ]:
                if col not in user_cols:
                    db.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
        db.commit()


def seed_currencies(user_id):
    db = get_db()
    for i, code in enumerate(ALL_CURRENCIES):
        unit, buy, sell, dec = DEFAULT_RATES.get(code, (1,0,0,2))
        db.execute(
            "INSERT INTO currencies (user_id,currency,unit,buying_rate,selling_rate,decimals,active,sort_order,updated_at) VALUES (?,?,?,?,?,?,TRUE,?,?)",
            (user_id, code, unit, buy, sell, dec, i, utc_now_naive())
        )
    db.commit()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorised"}), 401
        return f(*args, **kwargs)
    return decorated


def current_user_id():
    return session.get("user_id")


# ── Page routes ──

@app.route("/")
def index():
    return send_from_directory(CLIENT_DIR, "index.html")

@app.route("/login")
def login_page():
    return send_from_directory(CLIENT_DIR, "login.html")

@app.route("/signup")
def signup_page():
    return send_from_directory(CLIENT_DIR, "signup.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(CLIENT_DIR, path)


# ── Auth API ──

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    hashed = generate_password_hash(password)
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?) RETURNING id",
            (username, hashed)
        )
        new_id = cur.fetchone()["id"]
        db.commit()
        seed_currencies(new_id)
        return jsonify({"message": "Account created"})
    except (psycopg2.errors.UniqueViolation, sqlite3.IntegrityError):
        db.rollback()
        return jsonify({"error": "Username already exists"}), 400


@app.route("/api/login", methods=["POST"])
def login_user():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        count = db.execute("SELECT COUNT(*) AS count FROM currencies WHERE user_id=?", (user["id"],)).fetchone()["count"]
        if count == 0:
            seed_currencies(user["id"])
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
def me():
    if session.get("user_id"):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        return jsonify({
            "id": user["id"],
            "username": user["username"],
            "email": user["email"] if user["email"] else "",
            "displayName": user["display_name"] if user["display_name"] else "",
            "boardColor": user["board_color"] if user["board_color"] else DEFAULT_BOARD_COLOR,
            "rateColor": user["rate_color"] if user["rate_color"] else DEFAULT_RATE_COLOR,
            "logo": user["logo_data"] if user["logo_data"] else "",
            "boardName": user["board_name"] if user["board_name"] else "",
            "fontScale": user["font_scale"] if user["font_scale"] else DEFAULT_FONT_SCALE,
            "boardSubtitle": user["board_subtitle"] if user["board_subtitle"] else DEFAULT_BOARD_SUBTITLE,
            "boardLicense": user["board_license"] if user["board_license"] else DEFAULT_BOARD_LICENSE,
            "boardRegisterNo": user["board_register_no"] if user["board_register_no"] else "",
            "mobileNumber": user["mobile_number"] if user["mobile_number"] else "",
            "primaryDisplayCount": user["primary_display_count"] if user["primary_display_count"] else DEFAULT_PRIMARY_DISPLAY_COUNT,
            "secondaryGroupSize": user["secondary_group_size"] if user["secondary_group_size"] else DEFAULT_SECONDARY_GROUP_SIZE
        })
    return jsonify({"error": "Not logged in"}), 401


# ── Account settings API (profile + password) ──

@app.route("/api/account/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.json or {}
    display_name = data.get("displayName", "").strip()
    email        = data.get("email", "").strip()
    db = get_db()
    db.execute("UPDATE users SET display_name=?, email=? WHERE id=?",
               (display_name, email, current_user_id()))
    db.commit()
    return jsonify({"message": "Profile updated"})


@app.route("/api/account/password", methods=["PUT"])
@login_required
def update_password():
    data = request.json or {}
    current_password = data.get("currentPassword", "").strip()
    new_password     = data.get("newPassword", "").strip()
    confirm_password = data.get("confirmPassword", "").strip()

    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "All fields are required"}), 400
    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (current_user_id(),)).fetchone()
    if not user or not check_password_hash(user["password"], current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    db.execute("UPDATE users SET password=? WHERE id=?",
               (generate_password_hash(new_password), current_user_id()))
    db.commit()
    return jsonify({"message": "Password updated"})


# ── Board settings API (color + logo) ──

@app.route("/api/board", methods=["PUT"])
@login_required
def update_board():
    data = request.json or {}
    color      = data.get("boardColor", "").strip()
    rate_color = data.get("rateColor", "").strip()
    logo       = data.get("logo", None)  # None = leave unchanged, "" = clear, data URL = set
    board_name = data.get("boardName", None)  # None = leave unchanged
    font_scale = data.get("fontScale", None)  # None = leave unchanged
    subtitle   = data.get("boardSubtitle", None)  # None = leave unchanged
    license_txt= data.get("boardLicense", None)   # None = leave unchanged
    register_no= data.get("boardRegisterNo", None)  # None = leave unchanged
    mobile     = data.get("mobileNumber", None)   # None = leave unchanged
    primary_count = data.get("primaryDisplayCount", None)  # None = leave unchanged
    secondary_group_size = data.get("secondaryGroupSize", None)  # None = leave unchanged

    if color and not (color.startswith("#") and len(color) in (4, 7)):
        return jsonify({"error": "Invalid color"}), 400
    if rate_color and not (rate_color.startswith("#") and len(rate_color) in (4, 7)):
        return jsonify({"error": "Invalid rate color"}), 400
    if logo is not None and len(logo) > MAX_LOGO_LEN:
        return jsonify({"error": "Logo image is too large"}), 400
    if board_name is not None and len(board_name) > 80:
        return jsonify({"error": "Board name is too long"}), 400
    if subtitle is not None and len(subtitle) > MAX_TEXT_FIELD_LEN:
        return jsonify({"error": "Subtitle is too long"}), 400
    if license_txt is not None and len(license_txt) > MAX_TEXT_FIELD_LEN:
        return jsonify({"error": "License text is too long"}), 400
    if register_no is not None and len(register_no) > MAX_TEXT_FIELD_LEN:
        return jsonify({"error": "Register no. is too long"}), 400
    if mobile is not None and len(mobile) > 40:
        return jsonify({"error": "Mobile number is too long"}), 400
    if font_scale is not None:
        try:
            font_scale = float(font_scale)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid font size"}), 400
        if font_scale < MIN_FONT_SCALE or font_scale > MAX_FONT_SCALE:
            return jsonify({"error": "Font size out of range"}), 400
    if primary_count is not None:
        try:
            primary_count = int(primary_count)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid currency count"}), 400
        if primary_count < MIN_PRIMARY_DISPLAY_COUNT or primary_count > MAX_PRIMARY_DISPLAY_COUNT:
            return jsonify({"error": "Currency count out of range"}), 400
    if secondary_group_size is not None:
        try:
            secondary_group_size = int(secondary_group_size)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid rotation count"}), 400
        if secondary_group_size not in ALLOWED_SECONDARY_GROUP_SIZES:
            return jsonify({"error": "Rotation count must be 5 or 10"}), 400

    db = get_db()
    sets, params = [], []
    if color:
        sets.append("board_color=?")
        params.append(color)
    if rate_color:
        sets.append("rate_color=?")
        params.append(rate_color)
    if logo is not None:
        sets.append("logo_data=?")
        params.append(logo)
    if board_name is not None:
        sets.append("board_name=?")
        params.append(board_name.strip())
    if font_scale is not None:
        sets.append("font_scale=?")
        params.append(font_scale)
    if subtitle is not None:
        sets.append("board_subtitle=?")
        params.append(subtitle.strip())
    if license_txt is not None:
        sets.append("board_license=?")
        params.append(license_txt.strip())
    if register_no is not None:
        sets.append("board_register_no=?")
        params.append(register_no.strip())
    if mobile is not None:
        sets.append("mobile_number=?")
        params.append(mobile.strip())
    if primary_count is not None:
        sets.append("primary_display_count=?")
        params.append(primary_count)
    if secondary_group_size is not None:
        sets.append("secondary_group_size=?")
        params.append(secondary_group_size)
    if not sets:
        return jsonify({"message": "Nothing to update"})
    params.append(current_user_id())
    db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", params)
    db.commit()
    return jsonify({"message": "Board updated"})


# ── Currencies API ──

def row_to_dict(row, i=None):
    d = {
        "id":            row["id"],
        "currency":      row["currency"],
        "unit":          row["unit"] if row["unit"] else 1,
        "buyingRate":    row["buying_rate"],
        "sellingRate":   row["selling_rate"],
        "decimals":      row["decimals"],
        "active":        bool(row["active"]),
        "isPrimary":     row["currency"] in PRIMARY_CURRENCIES,
        "buyPreorder":   bool(row["buy_preorder"]),
        "sellPreorder":  bool(row["sell_preorder"]),
        "currencyName":  row["currency_name"] if row["currency_name"] else "",
        "currencyFlag":  row["currency_flag"] if row["currency_flag"] else "",
        "rowColor":      row["row_color"] if row["row_color"] else "",
    }
    if i is not None:
        d["serialNumber"] = i + 1
    return d


def parse_rate_field(data, rate_key, preorder_key):
    """A rate is either a number, or marked as pre-order (no number required)."""
    preorder = bool(data.get(preorder_key, False))
    if preorder:
        return 0.0, True
    value = data.get(rate_key)
    if value is None:
        return None, None
    try:
        return float(value), False
    except (ValueError, TypeError):
        return None, None


@app.route("/api/currencies", methods=["GET"])
@login_required
def get_currencies():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM currencies WHERE user_id=? ORDER BY sort_order, id",
        (current_user_id(),)
    ).fetchall()
    return jsonify([row_to_dict(r, i) for i, r in enumerate(rows)])


@app.route("/api/currencies", methods=["POST"])
@login_required
def add_currency():
    data = request.json or {}
    currency = data.get("currency", "").strip().upper()
    unit     = data.get("unit", 1)
    decimals = data.get("decimals", 2)
    currency_name = (data.get("currencyName") or "").strip()
    currency_flag = (data.get("currencyFlag") or "").strip().lower()

    buying_rate,  buy_preorder  = parse_rate_field(data, "buyingRate",  "buyPreorder")
    selling_rate, sell_preorder = parse_rate_field(data, "sellingRate", "sellPreorder")

    if not currency or buying_rate is None or selling_rate is None:
        return jsonify({"error": "All fields are required"}), 400
    try:
        unit = int(unit); decimals = int(decimals)
        if unit < 1: raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    db = get_db()
    existing = db.execute(
        "SELECT id FROM currencies WHERE user_id=? AND currency=?",
        (current_user_id(), currency)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE currencies SET unit=?, buying_rate=?, selling_rate=?, decimals=?, buy_preorder=?, sell_preorder=?, currency_name=?, currency_flag=?, updated_at=? WHERE id=? AND user_id=?",
            (unit, buying_rate, selling_rate, decimals, bool(buy_preorder), bool(sell_preorder), currency_name, currency_flag, utc_now_naive(), existing["id"], current_user_id())
        )
    else:
        max_order = db.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS max_order FROM currencies WHERE user_id=?",
            (current_user_id(),)
        ).fetchone()["max_order"]
        db.execute(
            "INSERT INTO currencies (user_id,currency,unit,buying_rate,selling_rate,decimals,active,sort_order,buy_preorder,sell_preorder,updated_at,currency_name,currency_flag) VALUES (?,?,?,?,?,?,TRUE,?,?,?,?,?,?)",
            (current_user_id(), currency, unit, buying_rate, selling_rate, decimals, max_order + 1, bool(buy_preorder), bool(sell_preorder), utc_now_naive(), currency_name, currency_flag)
        )
    db.commit()
    return jsonify({"message": "Currency saved"}), 201


@app.route("/api/currencies/<int:cid>", methods=["PUT"])
@login_required
def update_currency(cid):
    data = request.json or {}
    currency = data.get("currency", "").strip().upper()
    unit     = data.get("unit", 1)
    decimals = data.get("decimals", 2)
    currency_name = (data.get("currencyName") or "").strip()
    currency_flag = (data.get("currencyFlag") or "").strip().lower()
    row_color     = (data.get("rowColor") or "").strip()

    buying_rate,  buy_preorder  = parse_rate_field(data, "buyingRate",  "buyPreorder")
    selling_rate, sell_preorder = parse_rate_field(data, "sellingRate", "sellPreorder")

    if not currency or buying_rate is None or selling_rate is None:
        return jsonify({"error": "All fields are required"}), 400
    if row_color and not (row_color.startswith("#") and len(row_color) in (4, 7)):
        return jsonify({"error": "Invalid row color"}), 400
    try:
        unit = int(unit); decimals = int(decimals)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    db = get_db()
    dupe = db.execute(
        "SELECT id FROM currencies WHERE user_id=? AND currency=? AND id!=?",
        (current_user_id(), currency, cid)
    ).fetchone()
    if dupe:
        return jsonify({"error": f"{currency} already exists on your board"}), 409
    db.execute(
        "UPDATE currencies SET currency=?, buying_rate=?, selling_rate=?, decimals=?, unit=?, buy_preorder=?, sell_preorder=?, currency_name=?, currency_flag=?, row_color=?, updated_at=? WHERE id=? AND user_id=?",
        (currency, buying_rate, selling_rate, decimals, unit, bool(buy_preorder), bool(sell_preorder), currency_name, currency_flag, row_color, utc_now_naive(), cid, current_user_id())
    )
    db.commit()
    return jsonify({"message": "Updated"})


@app.route("/api/currencies/reorder", methods=["POST"])
@login_required
def reorder_currencies():
    data = request.json or {}
    order = data.get("order", [])
    if not isinstance(order, list) or not order:
        return jsonify({"error": "Invalid order"}), 400
    db = get_db()
    for idx, cid in enumerate(order):
        try:
            cid = int(cid)
        except (ValueError, TypeError):
            continue
        db.execute(
            "UPDATE currencies SET sort_order=? WHERE id=? AND user_id=?",
            (idx, cid, current_user_id())
        )
    db.commit()
    return jsonify({"message": "Reordered"})


@app.route("/api/currencies/<int:cid>/toggle", methods=["POST"])
@login_required
def toggle_currency(cid):
    db = get_db()
    row = db.execute(
        "SELECT active FROM currencies WHERE id=? AND user_id=?",
        (cid, current_user_id())
    ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    new_state = not row["active"]
    db.execute("UPDATE currencies SET active=?, updated_at=? WHERE id=? AND user_id=?",
               (new_state, utc_now_naive(), cid, current_user_id()))
    db.commit()
    return jsonify({"active": bool(new_state)})


@app.route("/api/currencies/<int:cid>", methods=["DELETE"])
@login_required
def delete_currency(cid):
    db = get_db()
    db.execute("DELETE FROM currencies WHERE id=? AND user_id=?", (cid, current_user_id()))
    db.commit()
    return jsonify({"message": "Deleted"})


# ── Public board (no login required — this is what the TV/display board reads) ──

@app.route("/api/board/public", methods=["GET"])
def public_board():
    user_id = request.args.get("user")
    if not user_id:
        return jsonify({"error": "Missing user"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "Board not found"}), 404
    rows = db.execute(
        "SELECT * FROM currencies WHERE user_id=? AND active=TRUE ORDER BY sort_order, id",
        (user_id,)
    ).fetchall()

    last_updated_row = db.execute(
        "SELECT MAX(updated_at) AS last_updated FROM currencies WHERE user_id=?",
        (user_id,)
    ).fetchone()
    last_updated = last_updated_row["last_updated"] if last_updated_row else None
    if last_updated is not None:
        # Postgres (psycopg2) returns a datetime object; SQLite returns a
        # plain string. Normalize to an ISO string and tag it as UTC so the
        # browser (new Date(...)) parses it correctly and converts it to
        # the viewer's local time, instead of assuming it's already local.
        # Also drop fractional seconds entirely — Postgres returns
        # microsecond precision, but the JS Date parser only reliably
        # handles 0 or 3 fractional digits, so anything else (e.g. 6-digit
        # microseconds) can silently produce an Invalid Date in the browser.
        if hasattr(last_updated, "isoformat"):
            last_updated = last_updated.replace(microsecond=0).isoformat()
        else:
            last_updated = last_updated.split(".")[0]
        if "T" not in last_updated:
            last_updated = last_updated.replace(" ", "T")
        if not last_updated.endswith("Z") and "+" not in last_updated:
            last_updated += "Z"

    resp = jsonify({
        "boardName":  user["board_name"] if user["board_name"] else "",
        "boardColor": user["board_color"] if user["board_color"] else DEFAULT_BOARD_COLOR,
        "rateColor":  user["rate_color"] if user["rate_color"] else DEFAULT_RATE_COLOR,
        "logo":       user["logo_data"] if user["logo_data"] else "",
        "fontScale":  user["font_scale"] if user["font_scale"] else DEFAULT_FONT_SCALE,
        "boardSubtitle": user["board_subtitle"] if user["board_subtitle"] else DEFAULT_BOARD_SUBTITLE,
        "boardLicense":  user["board_license"] if user["board_license"] else DEFAULT_BOARD_LICENSE,
        "boardRegisterNo": user["board_register_no"] if user["board_register_no"] else "",
        "mobileNumber":  user["mobile_number"] if user["mobile_number"] else "",
        "primaryDisplayCount": user["primary_display_count"] if user["primary_display_count"] else DEFAULT_PRIMARY_DISPLAY_COUNT,
        "secondaryGroupSize": user["secondary_group_size"] if user["secondary_group_size"] else DEFAULT_SECONDARY_GROUP_SIZE,
        "lastUpdated": last_updated,
        "currencies": [row_to_dict(r) for r in rows]
    })
    # This board data changes every time an admin edits a rate, and the
    # board page polls it every 15s (plus on-demand via BroadcastChannel) —
    # it must never be served stale from a browser or intermediary cache.
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


# Run schema creation / migrations on import, not just when this file is
# executed directly. Without this, running the app via gunicorn (as listed
# in requirements.txt) skips `init_db()` entirely, since gunicorn imports
# this module rather than running it as __main__ — new columns added to
# init_db() (e.g. board_color, logo_data) would silently never get applied
# to an existing database.db, causing endpoints like /api/me to 500.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)