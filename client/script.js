const API = "/products";

const form = document.getElementById("productForm");
const tableBody = document.getElementById("tableBody");

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

// ADD PRODUCT
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const product = {
        currency: document.getElementById("currency").value,
        buyingRate: Number(document.getElementById("buyingRate").value),
        sellingRate: Number(document.getElementById("sellingRate").value),
        quantity: Number(document.getElementById("quantity").value)
    };

    await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(product)
    });

    form.reset();
    loadProducts();
});

// DELETE PRODUCT
async function deleteProduct(id) {
    await fetch(`${API}/${id}`, { method: "DELETE" });
    loadProducts();
}

// EDIT → redirect to edit page
function editProduct(id) {
    window.location.href = `/edit?id=${id}`;
}

// INIT
loadProducts();