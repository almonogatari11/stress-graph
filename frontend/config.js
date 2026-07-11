const DEFAULT_API_BASE_URL = "https://stress-app-production.up.railway.app";

const API_BASE_URL = (
  window.__API_BASE_URL__ ||
  window.API_BASE_URL ||
  DEFAULT_API_BASE_URL
).replace(/\/$/, "");
