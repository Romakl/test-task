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
import { severityTone, shortTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { EventRecord } from "@cef/api-client";
import { Pause, Play, Trash2 } from "lucide-react";
import { Panel } from "./panel";

export function EventsPanel({
  events,
  paused,
  streamLive,
  onTogglePause,
  onClear,
}: {
  events: EventRecord[];
  paused: boolean;
  streamLive: boolean;
  onTogglePause: () => void;
  onClear: () => void;
}) {
  return (
    <Panel
      title="Live event decisions"
      bodyClassName="p-0"
      action={
        <div className="flex items-center gap-2">
          <Badge
            variant={streamLive && !paused ? "secondary" : "outline"}
            className={streamLive && !paused ? "text-emerald-400" : ""}
          >
            {paused ? "paused" : streamLive ? "live" : "connecting…"}
          </Badge>
          <Button variant="ghost" size="sm" onClick={onTogglePause}>
            {paused ? <Play /> : <Pause />}
            {paused ? "Resume" : "Pause"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onClear}>
            <Trash2 />
            Clear
          </Button>
        </div>
      }
    >
      <div className="max-h-[480px] overflow-auto">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-card">
            <TableRow>
              <TableHead className="w-14">#</TableHead>
              <TableHead>time</TableHead>
              <TableHead>source</TableHead>
              <TableHead>name</TableHead>
              <TableHead>sev</TableHead>
              <TableHead>action</TableHead>
              <TableHead>rule</TableHead>
              <TableHead>dest</TableHead>
              <TableHead>reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="py-10 text-center text-muted-foreground">
                  Waiting for events — send CEF traffic to the proxy to see live decisions.
                </TableCell>
              </TableRow>
            ) : null}
            {events.map((ev) => (
              <TableRow key={ev.seq} className={cn(!ev.parsed && "opacity-70")}>
                <TableCell className="tabular-nums text-muted-foreground">{ev.seq}</TableCell>
                <TableCell className="font-mono text-xs">{shortTime(ev.ts)}</TableCell>
                <TableCell className="font-mono text-xs">
                  {ev.source_ip}:{ev.source_port}
                </TableCell>
                <TableCell className="max-w-[22ch] truncate">
                  {ev.fields?.name ?? (ev.parsed ? "" : "⚠ unparsed")}
                </TableCell>
                <TableCell className={cn("tabular-nums", severityTone(ev.fields?.severity))}>
                  {ev.fields?.severity ?? ""}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      ev.action === "drop"
                        ? "destructive"
                        : ev.action === "forward"
                          ? "default"
                          : "outline"
                    }
                    className={ev.action === "forward" ? "bg-emerald-500/15 text-emerald-400" : ""}
                  >
                    {ev.action}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{ev.matched_rule_id ?? "—"}</TableCell>
                <TableCell className="font-mono text-xs">{ev.destination ?? "—"}</TableCell>
                <TableCell
                  className="max-w-[30ch] truncate text-xs text-muted-foreground"
                  title={ev.reason}
                >
                  {ev.reason}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}
