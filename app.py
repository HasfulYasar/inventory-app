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


# --- Database helpers ---

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
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT NOT NULL,
                buying_rate REAL NOT NULL,
                selling_rate REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
        ''')
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
                buying_rate REAL NOT NULL,
                selling_rate REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
        ''')
        db.commit()


# --- Auth helper ---

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

@app.route("/edit")
def edit_page():
    return send_from_directory(CLIENT_DIR, "edit.html")

@app.route("/add-currency")
def add_currency_page():
    return send_from_directory(CLIENT_DIR, "add-currency.html")

@app.route("/currency-list")
def currency_list_page():
    return send_from_directory(CLIENT_DIR, "currency-list.html")

@app.route("/edit-currency")
def edit_currency_page():
    return send_from_directory(CLIENT_DIR, "edit-currency.html")

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
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed)
        )
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
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"message": "Login successful"})
    else:
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


# --- Products API ---

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    db = get_db()
    rows = db.execute("SELECT * FROM products").fetchall()
    result = []
    for i, row in enumerate(rows):
        result.append({
            "id": row["id"],
            "serialNumber": i + 1,
            "currency": row["currency"],
            "buyingRate": row["buying_rate"],
            "sellingRate": row["selling_rate"],
            "quantity": row["quantity"]
        })
    return jsonify(result)


@app.route("/api/products/<int:product_id>", methods=["GET"])
@login_required
def get_product(product_id):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({
        "id": row["id"],
        "currency": row["currency"],
        "buyingRate": row["buying_rate"],
        "sellingRate": row["selling_rate"],
        "quantity": row["quantity"]
    })


@app.route("/api/products", methods=["POST"])
@login_required
def add_product():
    data = request.json or {}
    currency = data.get("currency", "").strip()
    buying_rate = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    quantity = data.get("quantity")

    if not currency or buying_rate is None or selling_rate is None or quantity is None:
        return jsonify({"error": "All fields are required"}), 400

    try:
        buying_rate = float(buying_rate)
        selling_rate = float(selling_rate)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric values"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO products (currency, buying_rate, selling_rate, quantity) VALUES (?, ?, ?, ?)",
        (currency, buying_rate, selling_rate, quantity)
    )
    db.commit()
    return jsonify({"message": "Product added"}), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@login_required
def update_product(product_id):
    data = request.json or {}
    currency = data.get("currency", "").strip()
    buying_rate = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    quantity = data.get("quantity")

    if not currency or buying_rate is None or selling_rate is None or quantity is None:
        return jsonify({"error": "All fields are required"}), 400

    try:
        buying_rate = float(buying_rate)
        selling_rate = float(selling_rate)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric values"}), 400

    db = get_db()
    db.execute(
        "UPDATE products SET currency=?, buying_rate=?, selling_rate=?, quantity=? WHERE id=?",
        (currency, buying_rate, selling_rate, quantity, product_id)
    )
    db.commit()
    return jsonify({"message": "Product updated"})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return jsonify({"message": "Product deleted"})


# --- Currencies API ---

@app.route("/api/currencies", methods=["GET"])
@login_required
def get_currencies():
    db = get_db()
    rows = db.execute("SELECT * FROM currencies").fetchall()
    result = []
    for i, row in enumerate(rows):
        result.append({
            "id": row["id"],
            "serialNumber": i + 1,
            "currency": row["currency"],
            "buyingRate": row["buying_rate"],
            "sellingRate": row["selling_rate"],
            "quantity": row["quantity"]
        })
    return jsonify(result)


@app.route("/api/currencies/<int:currency_id>", methods=["GET"])
@login_required
def get_currency(currency_id):
    db = get_db()
    row = db.execute("SELECT * FROM currencies WHERE id = ?", (currency_id,)).fetchone()
    if not row:
        return jsonify({"error": "Currency not found"}), 404
    return jsonify({
        "id": row["id"],
        "currency": row["currency"],
        "buyingRate": row["buying_rate"],
        "sellingRate": row["selling_rate"],
        "quantity": row["quantity"]
    })


@app.route("/api/currencies", methods=["POST"])
@login_required
def add_currency():
    data = request.json or {}
    currency = data.get("currency", "").strip()
    buying_rate = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    quantity = data.get("quantity")

    if not currency or buying_rate is None or selling_rate is None or quantity is None:
        return jsonify({"error": "All fields are required"}), 400

    try:
        buying_rate = float(buying_rate)
        selling_rate = float(selling_rate)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric values"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO currencies (currency, buying_rate, selling_rate, quantity) VALUES (?, ?, ?, ?)",
        (currency, buying_rate, selling_rate, quantity)
    )
    db.commit()
    return jsonify({"message": "Currency added"}), 201


@app.route("/api/currencies/<int:currency_id>", methods=["PUT"])
@login_required
def update_currency(currency_id):
    data = request.json or {}
    currency = data.get("currency", "").strip()
    buying_rate = data.get("buyingRate")
    selling_rate = data.get("sellingRate")
    quantity = data.get("quantity")

    if not currency or buying_rate is None or selling_rate is None or quantity is None:
        return jsonify({"error": "All fields are required"}), 400

    try:
        buying_rate = float(buying_rate)
        selling_rate = float(selling_rate)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric values"}), 400

    db = get_db()
    db.execute(
        "UPDATE currencies SET currency=?, buying_rate=?, selling_rate=?, quantity=? WHERE id=?",
        (currency, buying_rate, selling_rate, quantity, currency_id)
    )
    db.commit()
    return jsonify({"message": "Currency updated"})


@app.route("/api/currencies/<int:currency_id>", methods=["DELETE"])
@login_required
def delete_currency(currency_id):
    db = get_db()
    db.execute("DELETE FROM currencies WHERE id = ?", (currency_id,))
    db.commit()
    return jsonify({"message": "Currency deleted"})


# --- Run ---

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
