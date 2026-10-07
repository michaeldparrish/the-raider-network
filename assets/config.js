// The Raider Network configuration (v6.0)
//
// BACKEND
//   'auto'   (default) Use the Cloudflare API (Pages Functions + D1) whenever /api/health answers.
//            If there is no API AND the site is opened from a development host below (for example
//            `python3 -m http.server 8080` on localhost), fall back to the browser-only DEMO MODE.
//            A production domain never falls back to browser storage.
//   'server' Always require the API (demo fallback disabled even on localhost).
//   'demo'   Always use the browser-only demo (development only — never deploy with this).
//
// No secrets belong in this file: it is downloaded by every visitor.
window.RAIDER_CONFIG = {
  BACKEND: 'auto',
  DEMO_HOSTS: ['localhost', '127.0.0.1', '[::1]']
};
