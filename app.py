from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os

app = Flask(__name__)
CORS(app)

# ✅ Correct path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, "client")

# 📌 Database connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# 📌 Initialize tables
def init_db():
    conn = get_db()

    # Products table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT,
            buyingRate REAL,
            sellingRate REAL,
            quantity INTEGER
        )
    ''')

    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# 🌐 PAGE ROUTES

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
def edit():
    return send_from_directory(CLIENT_DIR, "edit.html")

# 🌐 STATIC FILES (JS, CSS)
@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(CLIENT_DIR, path)

# 🔐 AUTH APIs

# ➕ SIGNUP
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    conn = get_db()

    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        return jsonify({"message": "User created"})
    
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    
    finally:
        conn.close()


# 🔑 LOGIN
@app.route("/api/login", methods=["POST"])
def login_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()

    conn.close()

    if user:
        return jsonify({"message": "Login success"})
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# 📦 PRODUCTS APIs

# ➕ CREATE
@app.route("/products", methods=["POST"])
def add_product():
    data = request.json
    conn = get_db()

    conn.execute(
        "INSERT INTO products (currency, buyingRate, sellingRate, quantity) VALUES (?, ?, ?, ?)",
        (data["currency"], data["buyingRate"], data["sellingRate"], data["quantity"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Product added"})


# 📦 READ
@app.route("/products", methods=["GET"])
def get_products():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    result = []
    for i, row in enumerate(products):
        result.append({
            "id": row["id"],
            "serialNumber": i + 1,
            "currency": row["currency"],
            "buyingRate": row["buyingRate"],
            "sellingRate": row["sellingRate"],
            "quantity": row["quantity"]
        })

    return jsonify(result)


# ✏️ UPDATE
@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    data = request.json
    conn = get_db()

    conn.execute(
        "UPDATE products SET currency=?, buyingRate=?, sellingRate=?, quantity=? WHERE id=?",
        (data["currency"], data["buyingRate"], data["sellingRate"], data["quantity"], id)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Updated"})


# ❌ DELETE
@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    conn = get_db()

    conn.execute("DELETE FROM products WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Deleted"})


# ▶️ RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)