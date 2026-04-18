const API = "/api/products";

const params = new URLSearchParams(window.location.search);
const id = params.get("id");
const errorMsg = document.getElementById("error-msg");

function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
}

// Load just this one product by ID
async function loadProduct() {
    if (!id) {
        window.location.href = "/";
        return;
    }

    try {
        const res = await fetch(`${API}/${id}`, { credentials: "include" });

        if (res.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (res.status === 404) {
            showError("Product not found.");
            return;
        }
        if (!res.ok) throw new Error();

        const p = await res.json();
        document.getElementById("currency").value = p.currency;
        document.getElementById("buyingRate").value = p.buyingRate;
        document.getElementById("sellingRate").value = p.sellingRate;
        document.getElementById("quantity").value = p.quantity;

    } catch {
        showError("Could not load product. Please try again.");
    }
}

// Save updated product
async function saveProduct(e) {
    e.preventDefault();
    errorMsg.style.display = "none";

    const updated = {
        currency: document.getElementById("currency").value,
        buyingRate: Number(document.getElementById("buyingRate").value),
        sellingRate: Number(document.getElementById("sellingRate").value),
        quantity: Number(document.getElementById("quantity").value)
    };

    try {
        const res = await fetch(`${API}/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(updated)
        });

        if (!res.ok) {
            const data = await res.json();
            showError(data.error || "Failed to save changes");
            return;
        }

        window.location.href = "/";
    } catch {
        showError("Could not save changes. Please try again.");
    }
}

loadProduct();
