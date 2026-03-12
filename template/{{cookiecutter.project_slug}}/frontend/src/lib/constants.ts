/**
 * Application constants.
 */

export const APP_NAME = "{{ cookiecutter.project_name }}";
export const APP_DESCRIPTION = "{{ cookiecutter.project_description }}";

// API Routes (Next.js internal routes)
export const API_ROUTES = {
  // Auth
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",

  // Health
  HEALTH: "/health",

  // Users
  USERS: "/users",
{%- if cookiecutter.enable_ai_agent %}

  // Chat (AI Agent)
  CHAT: "/chat",
{%- endif %}
} as const;

// Navigation routes
export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/dashboard",
{%- if cookiecutter.enable_ai_agent %}
  CHAT: "/chat",
{%- endif %}
  PROFILE: "/profile",
  SETTINGS: "/settings",
} as const;
{%- if cookiecutter.enable_ai_agent %}

// WebSocket URL (for chat - this needs to be direct to backend for WS)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:{{ cookiecutter.backend_port }}";
{%- endif %}
