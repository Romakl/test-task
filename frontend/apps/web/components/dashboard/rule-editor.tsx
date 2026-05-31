"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  type Action,
  type Combinator,
  type Condition,
  KNOWN_FIELDS,
  LIST_OPS,
  NO_VALUE_OPS,
  OPERATORS,
  type Operator,
  type Rule,
} from "@cef/api-client";
import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

interface Row {
  uid: string;
  field: string;
  op: Operator;
  value: string;
  caseInsensitive: boolean;
}

function newUid(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

function toRow(condition: Condition): Row {
  const value = Array.isArray(condition.value)
    ? condition.value.join(", ")
    : condition.value === null || condition.value === undefined
      ? ""
      : String(condition.value);
  return {
    uid: newUid(),
    field: condition.field,
    op: condition.op,
    value,
    caseInsensitive: Boolean(condition.case_insensitive),
  };
}

function toConditions(rows: Row[]): Condition[] {
  return rows.map((row) => {
    const condition: Condition = {
      field: row.field,
      op: row.op,
      case_insensitive: row.caseInsensitive,
    };
    if (!NO_VALUE_OPS.has(row.op)) {
      if (row.op === "between") {
        condition.value = row.value.split(",").map((s) => s.trim());
      } else if (LIST_OPS.has(row.op)) {
        condition.value = row.value
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      } else {
        condition.value = row.value;
      }
    }
    return condition;
  });
}

export function RuleEditor({
  open,
  rule,
  onClose,
  onSubmit,
}: {
  open: boolean;
  rule: Rule | null;
  onClose: () => void;
  onSubmit: (rule: Rule, isEdit: boolean) => Promise<void>;
}) {
  const isEdit = rule !== null;
  const [id, setId] = useState("");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [combinator, setCombinator] = useState<Combinator>("all");
  const [action, setAction] = useState<Action>("forward");
  const [destHost, setDestHost] = useState("");
  const [destPort, setDestPort] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (rule) {
      setId(rule.id);
      setDescription(rule.description ?? "");
      setEnabled(rule.enabled ?? true);
      setCombinator(rule.match.combinator ?? "all");
      setAction(rule.action);
      setDestHost(rule.destination?.host ?? "");
      setDestPort(rule.destination ? String(rule.destination.port) : "");
      setRows(rule.match.conditions.map(toRow));
    } else {
      setId("");
      setDescription("");
      setEnabled(true);
      setCombinator("all");
      setAction("forward");
      setDestHost("");
      setDestPort("");
      setRows([{ uid: newUid(), field: "severity", op: "ge", value: "7", caseInsensitive: false }]);
    }
    setError(null);
  }, [open, rule]);

  function patchRow(uid: string, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.uid === uid ? { ...row, ...patch } : row)));
  }

  async function handleSave() {
    setError(null);
    if (!id.trim()) {
      setError("Rule id is required.");
      return;
    }
    const payload: Rule = {
      id: id.trim(),
      description: description.trim(),
      enabled,
      match: { combinator, conditions: toConditions(rows) },
      action,
    };
    if (action === "forward" && destHost.trim() && destPort.trim()) {
      payload.destination = { host: destHost.trim(), port: Number(destPort) };
    }
    setSaving(true);
    try {
      await onSubmit(payload, isEdit);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save rule");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? `Edit rule: ${rule?.id}` : "Add rule"}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label htmlFor="rule-id">ID</Label>
              <Input
                id="rule-id"
                value={id}
                disabled={isEdit}
                onChange={(e) => setId(e.target.value)}
                placeholder="forward-critical"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="rule-desc">Description</Label>
              <Input
                id="rule-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Forward all critical alerts"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-5">
            <div className="flex items-center gap-2">
              <Switch id="rule-enabled" checked={enabled} onCheckedChange={setEnabled} />
              <Label htmlFor="rule-enabled">Enabled</Label>
            </div>
            <div className="flex items-center gap-2">
              <Label>Match</Label>
              <Select value={combinator} onValueChange={(v) => setCombinator(v as Combinator)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">all (AND)</SelectItem>
                  <SelectItem value="any">any (OR)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <Label>Action</Label>
              <Select value={action} onValueChange={(v) => setAction(v as Action)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="forward">forward</SelectItem>
                  <SelectItem value="drop">drop</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {action === "forward" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid gap-1.5">
                <Label htmlFor="dest-host">
                  Dest host <span className="text-muted-foreground">(optional override)</span>
                </Label>
                <Input
                  id="dest-host"
                  value={destHost}
                  onChange={(e) => setDestHost(e.target.value)}
                  placeholder="(default ELK target)"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="dest-port">Dest port</Label>
                <Input
                  id="dest-port"
                  type="number"
                  value={destPort}
                  onChange={(e) => setDestPort(e.target.value)}
                  placeholder="(default ELK port)"
                />
              </div>
            </div>
          ) : null}

          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label>Conditions</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  setRows((current) => [
                    ...current,
                    {
                      uid: newUid(),
                      field: "filtertype",
                      op: "eq",
                      value: "",
                      caseInsensitive: false,
                    },
                  ])
                }
              >
                <Plus />
                Condition
              </Button>
            </div>
            {rows.map((row) => (
              <div
                key={row.uid}
                className="grid grid-cols-[1.1fr_1fr_1.3fr_auto_auto] items-center gap-2"
              >
                <Select
                  value={row.field}
                  onValueChange={(v) => patchRow(row.uid, { field: v ?? "" })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {KNOWN_FIELDS.map((field) => (
                      <SelectItem key={field} value={field}>
                        {field}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={row.op}
                  onValueChange={(v) => patchRow(row.uid, { op: v as Operator })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OPERATORS.map((op) => (
                      <SelectItem key={op} value={op}>
                        {op}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  value={row.value}
                  disabled={NO_VALUE_OPS.has(row.op)}
                  placeholder={
                    NO_VALUE_OPS.has(row.op)
                      ? "(no value)"
                      : LIST_OPS.has(row.op) || row.op === "between"
                        ? "a, b, c"
                        : "value"
                  }
                  onChange={(e) => patchRow(row.uid, { value: e.target.value })}
                />
                <Button
                  type="button"
                  variant={row.caseInsensitive ? "secondary" : "ghost"}
                  size="sm"
                  title="case-insensitive"
                  onClick={() => patchRow(row.uid, { caseInsensitive: !row.caseInsensitive })}
                >
                  ci
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  title="remove condition"
                  onClick={() => setRows((current) => current.filter((r) => r.uid !== row.uid))}
                >
                  <Trash2 />
                </Button>
              </div>
            ))}
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save rule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
