import { ApiClient, DEFAULT_API_BASE } from "@cef/api-client";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || DEFAULT_API_BASE;

const TOKEN_KEY = "cefproxy_token";

export function getToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

export function createApiClient(): ApiClient {
  return new ApiClient({ baseUrl: API_BASE, getToken });
}
