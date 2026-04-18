const API = "/api/products";

const form = document.getElementById("productForm");
const tableBody = document.getElementById("tableBody");
const errorMsg = document.getElementById("error-msg");

// Check auth via server on page load
async function checkAuth() {
    try {
        const res = await fetch("/api/me", { credentials: "include" });
        if (!res.ok) {
            window.location.href = "/login";
            return;
        }
        const data = await res.json();
        document.getElementById("welcome-msg").textContent = "Hi, " + data.username;
    } catch {
        window.location.href = "/login";
    }
}

function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
}

function hideError() {
    errorMsg.style.display = "none";
}

// Load all products
async function loadProducts() {
    try {
        const res = await fetch(API, { credentials: "include" });
        if (res.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (!res.ok) throw new Error("Failed to load products");

        const data = await res.json();
        hideError();

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
                        <button class="btn btn-small" onclick="editProduct(${p.id})">Edit</button>
                        <button class="btn btn-small btn-danger" onclick="deleteProduct(${p.id})">Delete</button>
                    </td>
                </tr>
            `;
        });
        tableBody.innerHTML = rows;
    } catch (err) {
        showError("Could not load products. Please refresh.");
    }
}

// Add product
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

// Delete product
async function deleteProduct(id) {
    if (!confirm("Delete this product?")) return;

    try {
        const res = await fetch(`${API}/${id}`, {
            method: "DELETE",
            credentials: "include"
        });

        if (!res.ok) throw new Error();
        loadProducts();
    } catch {
        showError("Could not delete product. Please try again.");
    }
}

// Edit — go to edit page
function editProduct(id) {
    window.location.href = `/edit?id=${id}`;
}

// Logout
async function logout() {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
    window.location.href = "/login";
}

// Init
checkAuth().then(() => loadProducts());
