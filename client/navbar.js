async function initPage() {
    try {
        const res = await fetch("/api/me", { credentials: "include" });
        if (!res.ok) { window.location.href = "/login"; return; }
        const data = await res.json();

        const logoSrc = data.logo ? data.logo : "/logo.png";
        const path = window.location.pathname;

        const nav = document.createElement("nav");
        nav.className = "navbar";
        nav.innerHTML = `
            <a href="/" class="nav-brand">
                <img src="${logoSrc}" alt="SHOWCASH" class="nav-logo">
            </a>
            <div class="nav-links">
                <a href="/" class="nav-link${path === "/" ? " active" : ""}">Home</a>
                <a href="/add-currency.html" class="nav-link${path === "/add-currency.html" ? " active" : ""}">+ Add Currency</a>
                <a href="/boards.html?user=${data.id}" target="_blank" class="nav-link">📺 Boards</a>
                <button class="btn btn-small btn-gold" id="navEditBtn" style="display:none;">✎ Edit</button>
            </div>
            <div class="nav-right">
                <a href="/account.html" class="nav-link${path === "/account.html" ? " active" : ""}">👤 Account</a>
                <span class="nav-user">Hi, ${data.displayName || data.username}</span>
                <button class="btn btn-small" style="background:#f0c040;color:#1a1a2e;border:none;font-weight:700;" onclick="doLogout()">Logout</button>
            </div>
        `;
        document.body.prepend(nav);

        const editBtn = document.getElementById("navEditBtn");
        if (editBtn && typeof window.toggleEditMode === "function") {
            editBtn.style.display = "inline-flex";
            editBtn.onclick = window.toggleEditMode;
        }
    } catch {
        window.location.href = "/login";
    }
}

async function doLogout() {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
    window.location.href = "/login";
}

initPage();
