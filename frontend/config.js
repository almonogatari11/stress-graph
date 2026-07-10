// config.js
// -----------
// Atur di sini alamat backend API Anda.
// Untuk local dev default ke localhost:8000.
// Untuk deploy, Anda bisa mengatur window.__API_BASE_URL__ atau window.API_BASE_URL.

const DEFAULT_API_BASE_URL =
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : (window.location.origin || "http://localhost:8000");

const API_BASE_URL = (
  window.__API_BASE_URL__ ||
  window.API_BASE_URL ||
  DEFAULT_API_BASE_URL
).replace(/\/$/, "");
