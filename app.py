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
                password TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS currencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT NOT NULL,
                unit INTEGER NOT NULL DEFAULT 1,
                buying_rate REAL NOT NULL,
                selling_rate REAL NOT NULL,
                decimals INTEGER NOT NULL DEFAULT 2,
                active INTEGER NOT NULL DEFAULT 1
            )
        ''')
        # Add unit column if it doesn't exist (for existing databases)
        try:
            db.execute("ALTER TABLE currencies ADD COLUMN unit INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass
        db.commit()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorised"}), 401
        return f(*args, **kwargs)
    return decorated


# --- Page routes ---

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

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(CLIENT_DIR, path)


# --- Auth API ---

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
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        db.commit()
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
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
def me():
    if session.get("user_id"):
        return jsonify({"username": session["username"]})
    return jsonify({"error": "Not logged in"}), 401


# --- Currencies API ---

def row_to_dict(row, i=None):
    d = {
        "id": row["id"],
        "currency": row["currency"],
        "unit": row["unit"] if row["unit"] else 1,
        "buyingRate": row["buying_rate"],
        "sellingRate": row["selling_rate"],
        "decimals": row["decimals"],
        "active": bool(row["active"])
    }
    if i is not None:
        d["serialNumber"] = i + 1
    return d


@app.route("/api/currencies", methods=["GET"])
@login_required
def get_currencies():
    db = get_db()
    rows = db.execute("SELECT * FROM currencies").fetchall()
    return jsonify([row_to_dict(r, i) for i, r in enumerate(rows)])


@app.route("/api/currencies/public", methods=["GET"])
def get_public_currencies():
    db = get_db()
    rows = db.execute("SELECT * FROM currencies WHERE active = 1").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/currencies/<int:cid>", methods=["GET"])
@login_required
def get_currency(cid):
    db = get_db()
    row = db.execute("SELECT * FROM currencies WHERE id = ?", (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/api/currencies", methods=["POST"])
@login_required
def add_currency():
    data = request.json or {}
    currency = data.get("currency", "").strip()
    unit = data.get("unit", 1)
    buying_rate = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    decimals = data.get("decimals", 2)
    if not currency or buying_rate is None or selling_rate is None:
        return jsonify({"error": "All fields are required"}), 400
    try:
        unit = int(unit)
        buying_rate = float(buying_rate)
        selling_rate = float(selling_rate)
        decimals = int(decimals)
        if unit < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    db = get_db()
    db.execute(
        "INSERT INTO currencies (currency, unit, buying_rate, selling_rate, decimals, active) VALUES (?, ?, ?, ?, ?, 1)",
        (currency, unit, buying_rate, selling_rate, decimals)
    )
    db.commit()
    return jsonify({"message": "Currency added"}), 201


@app.route("/api/currencies/<int:cid>", methods=["PUT"])
@login_required
def update_currency(cid):
    data = request.json or {}
    currency = data.get("currency", "").strip()
    unit = data.get("unit", 1)
    buying_rate = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    decimals = data.get("decimals", 2)
    if not currency or buying_rate is None or selling_rate is None:
        return jsonify({"error": "All fields are required"}), 400
    try:
        unit = int(unit)
        buying_rate = float(buying_rate)
        selling_rate = float(selling_rate)
        decimals = int(decimals)
        if unit < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid values"}), 400
    db = get_db()
    db.execute(
        "UPDATE currencies SET currency=?, unit=?, buying_rate=?, selling_rate=?, decimals=? WHERE id=?",
        (currency, unit, buying_rate, selling_rate, decimals, cid)
    )
    db.commit()
    return jsonify({"message": "Updated"})


@app.route("/api/currencies/<int:cid>/toggle", methods=["POST"])
@login_required
def toggle_currency(cid):
    db = get_db()
    row = db.execute("SELECT active FROM currencies WHERE id = ?", (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    new_state = 0 if row["active"] else 1
    db.execute("UPDATE currencies SET active=? WHERE id=?", (new_state, cid))
    db.commit()
    return jsonify({"active": bool(new_state)})


@app.route("/api/currencies/<int:cid>", methods=["DELETE"])
@login_required
def delete_currency(cid):
    db = get_db()
    db.execute("DELETE FROM currencies WHERE id = ?", (cid,))
    db.commit()
    return jsonify({"message": "Deleted"})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
