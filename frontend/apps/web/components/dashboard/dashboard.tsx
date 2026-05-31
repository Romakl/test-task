"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { API_BASE, createApiClient, getToken, setToken } from "@/lib/api";
import {
  type Action,
  ApiError,
  type EventRecord,
  type Health,
  type Rule,
  type RuleSet,
  type Stats,
  subscribeToEvents,
} from "@cef/api-client";
import { Filter, KeyRound, ShieldAlert, WifiOff } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { DryRun } from "./dry-run";
import { EventsPanel } from "./events-panel";
import { MetricsCards } from "./metrics-cards";
import { RuleEditor } from "./rule-editor";
import { RulesPanel } from "./rules-panel";

const MAX_EVENTS = 300;
const POLL_MS = 3000;

export function Dashboard() {
  const client = useMemo(() => createApiClient(), []);
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [ruleset, setRuleset] = useState<RuleSet | null>(null);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [paused, setPaused] = useState(false);
  const [streamLive, setStreamLive] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [reachable, setReachable] = useState(true);
  const [editor, setEditor] = useState<{ open: boolean; rule: Rule | null }>({
    open: false,
    rule: null,
  });

  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    setHasToken(Boolean(getToken()));
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, s, rs] = await Promise.all([client.health(), client.stats(), client.listRules()]);
      setHealth(h);
      setStats(s);
      setRuleset(rs);
      setReachable(true);
    } catch {
      setReachable(false);
    }
  }, [client]);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    let active = true;
    client
      .recentEvents(50)
      .then((recent) => {
        if (active) {
          setEvents(recent.slice().reverse());
        }
      })
      .catch(() => undefined);

    const source = subscribeToEvents(
      {
        onDecision: (record) => {
          if (pausedRef.current) {
            return;
          }
          setEvents((prev) => [record, ...prev].slice(0, MAX_EVENTS));
        },
        onOpen: () => setStreamLive(true),
        onError: () => setStreamLive(false),
      },
      API_BASE,
    );
    return () => {
      active = false;
      source.close();
    };
  }, [client]);

  function promptToken(): boolean {
    const next = window.prompt("Enter the API bearer token (required for mutations):", getToken());
    if (next === null) {
      return false;
    }
    const trimmed = next.trim();
    setToken(trimmed);
    setHasToken(Boolean(trimmed));
    return Boolean(trimmed);
  }

  async function runMutation(mutate: () => Promise<unknown>, success?: string) {
    try {
      await mutate();
      if (success) {
        toast.success(success);
      }
      await refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        toast.error("Unauthorized — set a valid API token.");
        promptToken();
      } else {
        toast.error(e instanceof Error ? e.message : "Request failed");
      }
    }
  }

  const rules = ruleset?.rules ?? [];

  async function handleSubmit(rule: Rule, isEdit: boolean) {
    try {
      if (isEdit) {
        await client.updateRule(rule.id, rule);
      } else {
        await client.createRule(rule);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        promptToken();
      }
      throw e;
    }
    toast.success(isEdit ? `Rule "${rule.id}" updated` : `Rule "${rule.id}" created`);
    await refresh();
  }

  function handleToggle(id: string) {
    const rule = rules.find((r) => r.id === id);
    if (!rule) {
      return;
    }
    void runMutation(() => client.updateRule(id, { ...rule, enabled: !(rule.enabled ?? true) }));
  }

  function handleMove(id: string, direction: -1 | 1) {
    const ids = rules.map((r) => r.id);
    const index = ids.indexOf(id);
    const swap = index + direction;
    if (swap < 0 || swap >= ids.length) {
      return;
    }
    const reordered = [...ids];
    const a = reordered[index];
    const b = reordered[swap];
    if (a === undefined || b === undefined) {
      return;
    }
    reordered[index] = b;
    reordered[swap] = a;
    void runMutation(() => client.reorderRules(reordered));
  }

  function handleDelete(id: string) {
    if (!window.confirm(`Delete rule "${id}"?`)) {
      return;
    }
    void runMutation(() => client.deleteRule(id), `Rule "${id}" deleted`);
  }

  function handleDefaultPolicy(policy: Action) {
    void runMutation(() => client.setDefaultPolicy(policy), `Default policy set to "${policy}"`);
  }

  const statusLine = !reachable
    ? "backend unreachable"
    : health
      ? `${health.env} · listening ${health.listen} → ${health.default_forward_target} · ${health.rules_count} rules · db ${health.database_ok ? "ok" : "down"} · uptime ${Math.round(health.uptime_seconds)}s`
      : "connecting…";

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Filter className="size-5" />
            </div>
            <div>
              <h1 className="font-heading text-base leading-tight font-semibold">
                CEF Filter Proxy
              </h1>
              <p className="font-mono text-xs text-muted-foreground">{statusLine}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">default policy</span>
              <Select
                value={health?.default_policy ?? "forward"}
                onValueChange={(v) => handleDefaultPolicy(v as Action)}
              >
                <SelectTrigger size="sm" className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="forward">forward (fail-open)</SelectItem>
                  <SelectItem value="drop">drop (fail-closed)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button variant="outline" size="sm" onClick={promptToken}>
              <KeyRound />
              {hasToken ? "Token set" : "Set token"}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-6 py-5">
        {!reachable ? (
          <Alert className="border-destructive/40 bg-destructive/10 text-destructive">
            <WifiOff />
            <AlertTitle>Backend unreachable</AlertTitle>
            <AlertDescription className="text-destructive/90">
              Could not reach the proxy API at {API_BASE}. Is the backend running (uvicorn on
              :8080)?
            </AlertDescription>
          </Alert>
        ) : null}

        {reachable && health && !health.auth_required ? (
          <Alert className="border-amber-500/40 bg-amber-500/10 text-amber-300">
            <ShieldAlert />
            <AlertTitle>Management API is unauthenticated</AlertTitle>
            <AlertDescription className="text-amber-300/90">
              No API token is set on the backend — mutating endpoints are open. Do not expose this
              beyond localhost.
            </AlertDescription>
          </Alert>
        ) : null}

        <MetricsCards stats={stats} />

        <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
          <RulesPanel
            ruleset={ruleset}
            ruleHits={stats?.rule_hits ?? {}}
            onAdd={() => setEditor({ open: true, rule: null })}
            onEdit={(id) => setEditor({ open: true, rule: rules.find((r) => r.id === id) ?? null })}
            onToggle={handleToggle}
            onMove={handleMove}
            onDelete={handleDelete}
          />
          <DryRun client={client} />
        </div>

        <EventsPanel
          events={events}
          paused={paused}
          streamLive={streamLive}
          onTogglePause={() => setPaused((p) => !p)}
          onClear={() => setEvents([])}
        />
      </main>

      <RuleEditor
        open={editor.open}
        rule={editor.rule}
        onClose={() => setEditor({ open: false, rule: null })}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
