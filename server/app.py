from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

# 📌 Create DB connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# 📌 Create table (only once)
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT,
            buyingRate REAL,
            sellingRate REAL,
            quantity INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ➕ CREATE
@app.route('/products', methods=['POST'])
def add_product():
    data = request.json
    conn = get_db()

    conn.execute(
        "INSERT INTO products (currency, buyingRate, sellingRate, quantity) VALUES (?, ?, ?, ?)",
        (data["currency"], data["buyingRate"], data["sellingRate"], data["quantity"])
    )
    conn.commit()

    return jsonify({"message": "Product added"})


# 📦 READ
@app.route('/products', methods=['GET'])
def get_products():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()

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
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    data = request.json
    conn = get_db()

    conn.execute(
        "UPDATE products SET currency=?, buyingRate=?, sellingRate=?, quantity=? WHERE id=?",
        (data["currency"], data["buyingRate"], data["sellingRate"], data["quantity"], id)
    )
    conn.commit()

    return jsonify({"message": "Updated"})


# ❌ DELETE
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()

    return jsonify({"message": "Deleted"})


# ▶️ RUN
if __name__ == '__main__':
    app.run(debug=True)