"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { matchSummary } from "@/lib/format";
import type { RuleSet } from "@cef/api-client";
import { ArrowDown, ArrowUp, Pencil, Plus, Power, Trash2 } from "lucide-react";
import { Panel } from "./panel";

export function RulesPanel({
  ruleset,
  ruleHits,
  onAdd,
  onEdit,
  onToggle,
  onMove,
  onDelete,
}: {
  ruleset: RuleSet | null;
  ruleHits: Record<string, number>;
  onAdd: () => void;
  onEdit: (id: string) => void;
  onToggle: (id: string) => void;
  onMove: (id: string, direction: -1 | 1) => void;
  onDelete: (id: string) => void;
}) {
  const rules = ruleset?.rules ?? [];

  return (
    <Panel
      title="Filter rules"
      subtitle="Evaluated top-down, first match wins. Unmatched events follow the default policy."
      bodyClassName="p-0"
      action={
        <Button size="sm" onClick={onAdd}>
          <Plus />
          Add rule
        </Button>
      }
    >
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">#</TableHead>
              <TableHead>ID</TableHead>
              <TableHead>On</TableHead>
              <TableHead>Match</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Dest</TableHead>
              <TableHead className="text-right">Hits</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rules.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                  No rules yet — unmatched events follow the default policy.
                </TableCell>
              </TableRow>
            ) : null}
            {rules.map((rule, index) => {
              const disabled = rule.enabled === false;
              return (
                <TableRow key={rule.id} className={disabled ? "opacity-60" : undefined}>
                  <TableCell className="tabular-nums text-muted-foreground">{index + 1}</TableCell>
                  <TableCell className="font-mono font-medium">{rule.id}</TableCell>
                  <TableCell>
                    <Badge variant={disabled ? "outline" : "secondary"}>
                      {disabled ? "off" : "on"}
                    </Badge>
                  </TableCell>
                  <TableCell
                    className="max-w-[30ch] truncate font-mono text-xs text-muted-foreground"
                    title={matchSummary(rule)}
                  >
                    {matchSummary(rule)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={rule.action === "drop" ? "destructive" : "default"}
                      className={
                        rule.action === "forward" ? "bg-emerald-500/15 text-emerald-400" : ""
                      }
                    >
                      {rule.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {rule.destination ? `${rule.destination.host}:${rule.destination.port}` : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {ruleHits[rule.id] ?? 0}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      title="move up"
                      disabled={index === 0}
                      onClick={() => onMove(rule.id, -1)}
                    >
                      <ArrowUp />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      title="move down"
                      disabled={index === rules.length - 1}
                      onClick={() => onMove(rule.id, 1)}
                    >
                      <ArrowDown />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      title={disabled ? "enable" : "disable"}
                      onClick={() => onToggle(rule.id)}
                    >
                      <Power />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      title="edit"
                      onClick={() => onEdit(rule.id)}
                    >
                      <Pencil />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      title="delete"
                      onClick={() => onDelete(rule.id)}
                    >
                      <Trash2 />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}
