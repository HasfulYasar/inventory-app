/* navbar.js — injects navbar and handles auth check on every page */

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/add-currency", label: "Add Currency" },
  { href: "/currency-list", label: "Currency List" },
];

async function initPage() {
  // Auth check
  try {
    const res = await fetch("/api/me", { credentials: "include" });
    if (!res.ok) { window.location.href = "/login"; return; }
    const data = await res.json();

    // Build navbar
    const current = window.location.pathname;
    const links = NAV_LINKS.map(l =>
      `<a href="${l.href}" class="nav-link ${current === l.href ? 'active' : ''}">${l.label}</a>`
    ).join("");

    const nav = document.createElement("nav");
    nav.className = "navbar";
    nav.innerHTML = `
      <div class="nav-brand">Inventory App</div>
      <div class="nav-links">${links}</div>
      <div class="nav-right">
        <span class="nav-user">Hi, ${data.username}</span>
        <button class="btn btn-secondary btn-small" onclick="doLogout()">Logout</button>
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
