(function () {
    const cookieName = "timezone";
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

    if (document.cookie.split("; ").some(row => row.startsWith(cookieName + "="))) {
        return;
    }

    const expires = new Date();
    expires.setDate(expires.getDate() + 7);
    document.cookie = `${cookieName}=${encodeURIComponent(tz)}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
})();
