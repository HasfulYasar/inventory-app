const NAV_LINKS = [
    { href: "/", label: "Home" },
    { href: "/add-currency", label: "Add Currency" },
];

async function initPage() {
    try {
        const res = await fetch("/api/me", { credentials: "include" });
        if (!res.ok) { window.location.href = "/login"; return; }
        const data = await res.json();

        const current = window.location.pathname;
        const links = NAV_LINKS.map(l =>
            `<a href="${l.href}" class="nav-link ${current === l.href ? 'active' : ''}">${l.label}</a>`
        ).join("");

        // Boards link includes user id so the board is user-specific
        const boardsActive = current === "/boards" ? 'active' : '';
        const boardsLink = `<a href="/boards?user=${data.id}" class="nav-link ${boardsActive}">Boards</a>`;

        const nav = document.createElement("nav");
        nav.className = "navbar";
        nav.innerHTML = `
            <a href="/" class="nav-brand">
                <img src="/logo.png" alt="SHOWCASH" class="nav-logo">
            </a>
            <div class="nav-links">${links}${boardsLink}</div>
            <div class="nav-right">
                <span class="nav-user">Hi, ${data.username}</span>
                <button class="btn btn-small" style="background:#f0c040;color:#1a1a2e;border:none;font-weight:700;" onclick="doLogout()">Logout</button>
            </div>
        `;
        document.body.prepend(nav);
    } catch {
        window.location.href = "/login";
    }
}

async function doLogout() {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
    window.location.href = "/login";
}

initPage();
