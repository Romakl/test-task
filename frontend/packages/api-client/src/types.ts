export const OPERATORS = [
  "eq",
  "ne",
  "in",
  "not_in",
  "contains",
  "not_contains",
  "regex",
  "not_regex",
  "cidr",
  "not_cidr",
  "gt",
  "ge",
  "lt",
  "le",
  "between",
  "exists",
  "not_exists",
] as const;
export type Operator = (typeof OPERATORS)[number];

export const KNOWN_FIELDS = [
  "eventid",
  "filterhostname",
  "filterid",
  "filteripaddress",
  "filternodename",
  "filterpriority",
  "filtertype",
  "notificationtime",
  "name",
  "severity",
] as const;
export type KnownField = (typeof KNOWN_FIELDS)[number];

export type Action = "forward" | "drop";
export type Combinator = "all" | "any";

export type ConditionValue = string | number | boolean | Array<string | number> | null;

export interface Condition {
  field: string;
  op: Operator;
  value?: ConditionValue;
  case_insensitive?: boolean;
}

export interface Match {
  combinator?: Combinator;
  conditions: Condition[];
}

export interface Destination {
  host: string;
  port: number;
}

export interface Rule {
  id: string;
  description?: string;
  enabled?: boolean;
  match: Match;
  action: Action;
  destination?: Destination | null;
}

export interface RuleSet {
  default_policy?: Action | null;
  rules: Rule[];
}

export interface Decision {
  action: Action;
  matched_rule_id?: string | null;
  matched_rule_description?: string | null;
  destination_host?: string | null;
  destination_port?: number | null;
  reason: string;
}

export interface EventRecord {
  seq: number;
  ts: string;
  source_ip: string;
  source_port: number;
  size_bytes: number;
  parsed: boolean;
  parse_error?: string | null;
  action: string;
  matched_rule_id?: string | null;
  reason: string;
  destination?: string | null;
  fields: Record<string, string>;
  raw_preview: string;
}

export interface Stats {
  uptime_seconds: number;
  datagrams_received: number;
  bytes_received: number;
  parse_ok: number;
  parse_errors: number;
  forwarded: number;
  dropped: number;
  forward_errors: number;
  source_rejected: number;
  rate_limited: number;
  queue_overflow: number;
  oversized: number;
  rule_hits: Record<string, number>;
}

export interface Health {
  status: string;
  app: string;
  env: string;
  uptime_seconds: number;
  listen: string;
  default_forward_target: string;
  rules_count: number;
  default_policy: string;
  auth_required: boolean;
  database_ok: boolean;
}

export interface DryRunResponse {
  parsed: boolean;
  parse_error?: string | null;
  event?: Record<string, string> | null;
  decision?: Decision | null;
  would_forward_to?: string | null;
}

export const LIST_OPS = new Set<Operator>(["in", "not_in", "cidr", "not_cidr"]);
export const NO_VALUE_OPS = new Set<Operator>(["exists", "not_exists"]);
