from flask import Flask, request, jsonify, send_from_directory, session, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
CORS(app, supports_credentials=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, "client")
DB_PATH = os.path.join(BASE_DIR, "database.db")

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
    "KWD","LKR","BDT","MOP","SCR","IQD"
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
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
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
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 999,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # Migrations for existing DBs
        for col, defn in [
            ("unit",         "INTEGER NOT NULL DEFAULT 1"),
            ("user_id",      "INTEGER NOT NULL DEFAULT 0"),
            ("sort_order",   "INTEGER NOT NULL DEFAULT 999"),
        ]:
            try:
                db.execute(f"ALTER TABLE currencies ADD COLUMN {col} {defn}")
            except Exception:
                pass
        for col, defn in [
            ("email",        "TEXT NOT NULL DEFAULT ''"),
            ("display_name", "TEXT NOT NULL DEFAULT ''"),
        ]:
            try:
                db.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            except Exception:
                pass
        db.commit()


def seed_currencies(user_id):
    db = get_db()
    for i, code in enumerate(ALL_CURRENCIES):
        unit, buy, sell, dec = DEFAULT_RATES.get(code, (1,0,0,2))
        db.execute(
            "INSERT INTO currencies (user_id,currency,unit,buying_rate,selling_rate,decimals,active,sort_order) VALUES (?,?,?,?,?,?,1,?)",
            (user_id, code, unit, buy, sell, dec, i)
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

@app.route("/add-currency")
def add_currency_page():
    return send_from_directory(CLIENT_DIR, "add-currency.html")

@app.route("/boards")
def boards_page():
    return send_from_directory(CLIENT_DIR, "boards.html")

@app.route("/account")
def account_page():
    return send_from_directory(CLIENT_DIR, "account.html")

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
        cur = db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        db.commit()
        seed_currencies(cur.lastrowid)
        return jsonify({"message": "Account created"})
    except sqlite3.IntegrityError:
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
        count = db.execute("SELECT COUNT(*) FROM currencies WHERE user_id=?", (user["id"],)).fetchone()[0]
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
            "displayName": user["display_name"] if user["display_name"] else ""
        })
    return jsonify({"error": "Not logged in"}), 401


# ── Account API ──

@app.route("/api/account/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.json or {}
    email        = data.get("email", "").strip()
    display_name = data.get("displayName", "").strip()
    db = get_db()
    db.execute(
        "UPDATE users SET email=?, display_name=? WHERE id=?",
        (email, display_name, current_user_id())
    )
    db.commit()
    return jsonify({"message": "Profile updated"})


@app.route("/api/account/password", methods=["PUT"])
@login_required
def change_password():
    data = request.json or {}
    current  = data.get("currentPassword", "").strip()
    new_pass = data.get("newPassword", "").strip()
    confirm  = data.get("confirmPassword", "").strip()
    if not current or not new_pass or not confirm:
        return jsonify({"error": "All fields are required"}), 400
    if new_pass != confirm:
        return jsonify({"error": "New passwords do not match"}), 400
    if len(new_pass) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (current_user_id(),)).fetchone()
    if not check_password_hash(user["password"], current):
        return jsonify({"error": "Current password is incorrect"}), 401
    db.execute("UPDATE users SET password=? WHERE id=?",
               (generate_password_hash(new_pass), current_user_id()))
    db.commit()
    return jsonify({"message": "Password changed successfully"})


# ── Currencies API ──

def row_to_dict(row, i=None):
    d = {
        "id":          row["id"],
        "currency":    row["currency"],
        "unit":        row["unit"] if row["unit"] else 1,
        "buyingRate":  row["buying_rate"],
        "sellingRate": row["selling_rate"],
        "decimals":    row["decimals"],
        "active":      bool(row["active"]),
        "isPrimary":   row["currency"] in PRIMARY_CURRENCIES,
    }
    if i is not None:
        d["serialNumber"] = i + 1
    return d


@app.route("/api/currencies", methods=["GET"])
@login_required
def get_currencies():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM currencies WHERE user_id=? ORDER BY sort_order, id",
        (current_user_id(),)
    ).fetchall()
    return jsonify([row_to_dict(r, i) for i, r in enumerate(rows)])


@app.route("/api/currencies/public", methods=["GET"])
def get_public_currencies():
    user_id = request.args.get("user")
    if not user_id:
        return jsonify([])
    db = get_db()
    rows = db.execute(
        "SELECT * FROM currencies WHERE user_id=? AND active=1 ORDER BY sort_order, id",
        (user_id,)
    ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/currencies", methods=["POST"])
@login_required
def add_currency():
    data = request.json or {}
    currency     = data.get("currency", "").strip()
    unit         = data.get("unit", 1)
    buying_rate  = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    decimals     = data.get("decimals", 2)
    if not currency or buying_rate is None or selling_rate is None:
        return jsonify({"error": "All fields are required"}), 400
    try:
        unit = int(unit); buying_rate = float(buying_rate)
        selling_rate = float(selling_rate); decimals = int(decimals)
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
            "UPDATE currencies SET unit=?, buying_rate=?, selling_rate=?, decimals=? WHERE id=? AND user_id=?",
            (unit, buying_rate, selling_rate, decimals, existing["id"], current_user_id())
        )
    else:
        db.execute(
            "INSERT INTO currencies (user_id,currency,unit,buying_rate,selling_rate,decimals,active,sort_order) VALUES (?,?,?,?,?,?,1,999)",
            (current_user_id(), currency, unit, buying_rate, selling_rate, decimals)
        )
    db.commit()
    return jsonify({"message": "Currency saved"}), 201


@app.route("/api/currencies/<int:cid>", methods=["PUT"])
@login_required
def update_currency(cid):
    data = request.json or {}
    currency     = data.get("currency", "").strip()
    unit         = data.get("unit", 1)
    buying_rate  = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    decimals     = data.get("decimals", 2)
    if not currency or buying_rate is None or selling_rate is None:
        return jsonify({"error": "All fields are required"}), 400
    try:
        unit = int(unit); buying_rate = float(buying_rate)
        selling_rate = float(selling_rate); decimals = int(decimals)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    db = get_db()
    db.execute(
        "UPDATE currencies SET buying_rate=?, selling_rate=?, decimals=?, unit=? WHERE id=? AND user_id=?",
        (buying_rate, selling_rate, decimals, unit, cid, current_user_id())
    )
    db.commit()
    return jsonify({"message": "Updated"})


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
    new_state = 0 if row["active"] else 1
    db.execute("UPDATE currencies SET active=? WHERE id=? AND user_id=?",
               (new_state, cid, current_user_id()))
    db.commit()
    return jsonify({"active": bool(new_state)})


@app.route("/api/currencies/<int:cid>", methods=["DELETE"])
@login_required
def delete_currency(cid):
    db = get_db()
    db.execute("DELETE FROM currencies WHERE id=? AND user_id=?", (cid, current_user_id()))
    db.commit()
    return jsonify({"message": "Deleted"})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
