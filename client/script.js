const API = "/api/products";

const form = document.getElementById("productForm");
const tableBody = document.getElementById("tableBody");
const errorMsg = document.getElementById("error-msg");

function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
}

function hideError() {
    errorMsg.style.display = "none";
}

async function loadProducts() {
    try {
        const res = await fetch(API, { credentials: "include" });
        if (res.status === 401) { window.location.href = "/login"; return; }
        if (!res.ok) throw new Error();

        const data = await res.json();
        hideError();

        if (data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="empty-state">No products yet. Add one above.</td></tr>`;
            return;
        }

        let rows = "";
        data.forEach(p => {
            rows += `
                <tr>
                    <td>${p.serialNumber}</td>
                    <td>${p.currency}</td>
                    <td>${p.buyingRate}</td>
                    <td>${p.sellingRate}</td>
                    <td>${p.quantity}</td>
                    <td>
                        <button class="btn btn-small btn-secondary" onclick="editProduct(${p.id})">Edit</button>
                        <button class="btn btn-small btn-danger" onclick="deleteProduct(${p.id})">Delete</button>
                    </td>
                </tr>
            `;
        });
        tableBody.innerHTML = rows;
    } catch {
        showError("Could not load products. Please refresh.");
    }
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();

    const product = {
        currency: document.getElementById("currency").value,
        buyingRate: Number(document.getElementById("buyingRate").value),
        sellingRate: Number(document.getElementById("sellingRate").value),
        quantity: Number(document.getElementById("quantity").value)
    };

    try {
        const res = await fetch(API, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(product)
        });

        if (!res.ok) {
            const data = await res.json();
            showError(data.error || "Failed to add product");
            return;
        }

        form.reset();
        loadProducts();
    } catch {
        showError("Could not add product. Please try again.");
    }
});

async function deleteProduct(id) {
    if (!confirm("Delete this product?")) return;
    try {
        const res = await fetch(`${API}/${id}`, { method: "DELETE", credentials: "include" });
        if (!res.ok) throw new Error();
        loadProducts();
    } catch {
        showError("Could not delete product. Please try again.");
    }
}

function editProduct(id) {
    window.location.href = `/edit?id=${id}`;
}

loadProducts();
