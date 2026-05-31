import type { Action, DryRunResponse, EventRecord, Health, Rule, RuleSet, Stats } from "./types";

export const DEFAULT_API_BASE = "http://localhost:8080";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface ApiClientOptions {
  baseUrl?: string;
  getToken?: () => string | null | undefined;
}

export class ApiClient {
  readonly baseUrl: string;
  private readonly getToken: () => string | null | undefined;

  constructor(opts: ApiClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? DEFAULT_API_BASE).replace(/\/$/, "");
    this.getToken = opts.getToken ?? (() => undefined);
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {};
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    const token = this.getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = (await res.json()) as { detail?: string };
        if (data?.detail) {
          detail = data.detail;
        }
      } catch {
        // non-JSON error body: keep statusText
      }
      throw new ApiError(res.status, detail);
    }

    if (res.status === 204) {
      return undefined as T;
    }
    return (await res.json()) as T;
  }

  health(): Promise<Health> {
    return this.request<Health>("GET", "/health");
  }

  stats(): Promise<Stats> {
    return this.request<Stats>("GET", "/api/stats");
  }

  listRules(): Promise<RuleSet> {
    return this.request<RuleSet>("GET", "/api/rules");
  }

  createRule(rule: Rule): Promise<Rule> {
    return this.request<Rule>("POST", "/api/rules", rule);
  }

  updateRule(id: string, rule: Rule): Promise<Rule> {
    return this.request<Rule>("PUT", `/api/rules/${encodeURIComponent(id)}`, rule);
  }

  deleteRule(id: string): Promise<void> {
    return this.request<void>("DELETE", `/api/rules/${encodeURIComponent(id)}`);
  }

  reorderRules(order: string[]): Promise<RuleSet> {
    return this.request<RuleSet>("POST", "/api/rules/reorder", { order });
  }

  setDefaultPolicy(policy: Action): Promise<RuleSet> {
    return this.request<RuleSet>("PUT", "/api/rules/settings/default-policy", {
      default_policy: policy,
    });
  }

  dryRun(raw: string): Promise<DryRunResponse> {
    return this.request<DryRunResponse>("POST", "/api/dry-run", { raw });
  }

  recentEvents(limit = 100): Promise<EventRecord[]> {
    return this.request<EventRecord[]>("GET", `/api/events?limit=${limit}`);
  }
}
