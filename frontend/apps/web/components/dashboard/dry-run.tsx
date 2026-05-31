"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ApiClient, DryRunResponse } from "@cef/api-client";
import { useState } from "react";
import { Panel } from "./panel";

const PLACEHOLDER =
  "CEF:0|Acme|FilterEngine|1.0|1001|Port scan detected|8|eventid=1001 filtertype=ids filteripaddress=10.0.0.5 filterpriority=9";

export function DryRun({ client }: { client: ApiClient }) {
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<DryRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (!raw.trim()) {
      setError("Enter a CEF line to evaluate.");
      setResult(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await client.dryRun(raw));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const action = result?.decision?.action;

  return (
    <Panel
      title="Dry-run tester"
      subtitle="Evaluate a raw CEF/Syslog line against the live ruleset — no forwarding."
    >
      <div className="grid gap-3">
        <Textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          rows={4}
          spellCheck={false}
          placeholder={PLACEHOLDER}
          className="resize-y font-mono text-xs"
        />
        <div>
          <Button onClick={run} disabled={loading}>
            {loading ? "Evaluating…" : "Evaluate"}
          </Button>
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {result ? (
          result.parsed ? (
            <div className="rounded-lg border bg-muted/30 p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={action === "drop" ? "destructive" : "default"}
                  className={action === "forward" ? "bg-emerald-500/15 text-emerald-400" : ""}
                >
                  {action?.toUpperCase()}
                </Badge>
                <span className="text-muted-foreground">
                  {result.decision?.matched_rule_id
                    ? `rule ${result.decision.matched_rule_id}`
                    : "default policy"}
                </span>
                {result.would_forward_to ? (
                  <span className="font-mono text-xs text-muted-foreground">
                    → {result.would_forward_to}
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{result.decision?.reason}</p>
              {result.event ? (
                <div className="mt-3 grid gap-0.5 font-mono text-xs">
                  {Object.entries(result.event).map(([k, v]) => (
                    <div key={k} className="flex gap-2">
                      <span className="w-40 shrink-0 text-muted-foreground">{k}</span>
                      <span className="break-all">{v}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              Parse error: {result.parse_error}
            </div>
          )
        ) : null}
      </div>
    </Panel>
  );
}
