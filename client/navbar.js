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
                <a href="/board-settings.html" class="nav-link${path === "/board-settings.html" ? " active" : ""}">⚙ Board Settings</a>
                <a href="/boards.html?user=${data.id}" class="nav-link" target="_blank" rel="noopener">📺 Boards</a>
                <button class="btn btn-small btn-gold" id="navEditBtn">✎ Edit</button>
            </div>
            <div class="nav-right">
                <a href="/account.html" class="nav-link${path === "/account.html" ? " active" : ""}">👤 Account</a>
                <span class="nav-user">Hi, ${data.displayName || data.username}</span>
                <button class="btn btn-small" style="background:#f0c040;color:#1a1a2e;border:none;font-weight:700;" onclick="doLogout()">Logout</button>
            </div>
        `;
        document.body.prepend(nav);

        const editBtn = document.getElementById("navEditBtn");
        if (editBtn) {
            if (typeof window.toggleEditMode === "function") {
                // Already on the home page — toggle edit mode directly.
                editBtn.onclick = window.toggleEditMode;
            } else {
                // On another page — go home and ask it to enter edit mode
                // as soon as it loads.
                editBtn.onclick = () => {
                    sessionStorage.setItem("showcash_enter_edit", "1");
                    window.location.href = "/";
                };
            }
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
