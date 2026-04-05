const API = "http://127.0.0.1:5000/products";

const form = document.getElementById("productForm");
const tableBody = document.getElementById("tableBody");

let editId = null;

// LOAD DATA
async function loadProducts() {
    const res = await fetch(API);
    const data = await res.json();

    tableBody.innerHTML = "";

    data.forEach(p => {
        tableBody.innerHTML += `
            <tr>
                <td>${p.serialNumber}</td>
                <td>${p.currency}</td>
                <td>${p.buyingRate}</td>
                <td>${p.sellingRate}</td>
                <td>${p.quantity}</td>
                <td>
                    <button onclick="editProduct(${p.id})">Edit</button>
                    <button onclick="deleteProduct(${p.id})">Delete</button>
                </td>
            </tr>
        `;
    });
}

// ADD / UPDATE
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const product = {
        currency: document.getElementById("currency").value,
        buyingRate: Number(document.getElementById("buyingRate").value),
        sellingRate: Number(document.getElementById("sellingRate").value),
        quantity: Number(document.getElementById("quantity").value)
    };

    if (editId) {
        await fetch(`${API}/${editId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(product)
        });
        editId = null;
    } else {
        await fetch(API, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(product)
        });
    }

    form.reset();
    loadProducts();
});

// DELETE
async function deleteProduct(id) {
    await fetch(`${API}/${id}`, { method: "DELETE" });
    loadProducts();
}

// EDIT
async function editProduct(id) {
    const res = await fetch(API);
    const data = await res.json();

    const p = data.find(item => item.id === id);

    document.getElementById("currency").value = p.currency;
    document.getElementById("buyingRate").value = p.buyingRate;
    document.getElementById("sellingRate").value = p.sellingRate;
    document.getElementById("quantity").value = p.quantity;

    editId = id;
}

// INIT
loadProducts();