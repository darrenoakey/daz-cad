/**
 * Resolve app URLs when daz-cad is opened directly or through the auto-gui proxy.
 *
 * Auto-gui iframes the app at /proxy/daz-cad/ on the dashboard origin. Root-absolute
 * /static and /api URLs then hit the dashboard, not daz-cad. Fetch is shimmed;
 * dynamic import() and Worker URLs are not.
 */

export function appBase(pathname = globalThis.location?.pathname || "") {
    const match = String(pathname).match(/^(\/proxy\/[^/]+)(?:\/|$)/);
    return match ? match[1] : "";
}

export function appUrl(path, pathname = globalThis.location?.pathname || "") {
    if (!path || /^(https?:|data:|blob:)/.test(path)) return path;
    const normalized = path.startsWith("/") ? path : `/${path}`;
    return `${appBase(pathname)}${normalized}`;
}
