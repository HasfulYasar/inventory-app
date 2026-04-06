const API = "/products";

// Get ID from URL
const params = new URLSearchParams(window.location.search);
const id = params.get("id");

// Load product data
async function loadProduct() {
    const res = await fetch(API);
    const data = await res.json();

    const p = data.find(item => item.id == id);

    if (!p) {
        alert("Product not found");
        window.location.href = "/";
        return;
    }

    document.getElementById("currency").value = p.currency;
    document.getElementById("buyingRate").value = p.buyingRate;
    document.getElementById("sellingRate").value = p.sellingRate;
    document.getElementById("quantity").value = p.quantity;
}

loadProduct();

// Save updated product
document.getElementById("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const updatedProduct = {
        currency: document.getElementById("currency").value,
        buyingRate: Number(document.getElementById("buyingRate").value),
        sellingRate: Number(document.getElementById("sellingRate").value),
        quantity: Number(document.getElementById("quantity").value)
    };

    await fetch(`${API}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedProduct)
    });

    // Go back to main page
    window.location.href = "/";
});