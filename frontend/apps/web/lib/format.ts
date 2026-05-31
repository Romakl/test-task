import { NO_VALUE_OPS, type Rule } from "@cef/api-client";

export function matchSummary(rule: Rule): string {
  const parts = rule.match.conditions.map((c) => {
    if (NO_VALUE_OPS.has(c.op)) {
      return `${c.field} ${c.op}`;
    }
    const value = Array.isArray(c.value)
      ? `[${c.value.join(", ")}]`
      : c.value === null || c.value === undefined
        ? ""
        : String(c.value);
    return `${c.field} ${c.op} ${value}`;
  });
  const joiner = rule.match.combinator === "any" ? "  OR  " : "  AND  ";
  return parts.join(joiner) || "(no conditions)";
}

export function shortTime(ts: string): string {
  return ts.length >= 19 ? ts.slice(11, 19) : ts;
}

export function severityTone(severity: string | undefined): string {
  if (!severity) {
    return "text-muted-foreground";
  }
  const word = severity.toLowerCase();
  const numeric = Number(severity);
  const value = Number.isNaN(numeric)
    ? word.includes("very") || word === "high"
      ? 9
      : word === "medium"
        ? 5
        : 1
    : numeric;
  if (value >= 9) {
    return "text-red-400";
  }
  if (value >= 7) {
    return "text-amber-400";
  }
  if (value >= 4) {
    return "text-yellow-400";
  }
  return "text-muted-foreground";
}
