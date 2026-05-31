"use client";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Stats } from "@cef/api-client";

const CARDS: Array<{ key: keyof Stats; label: string; tone?: string }> = [
  { key: "datagrams_received", label: "Received" },
  { key: "forwarded", label: "Forwarded", tone: "text-emerald-400" },
  { key: "dropped", label: "Dropped", tone: "text-amber-400" },
  { key: "parse_errors", label: "Parse errors" },
  { key: "forward_errors", label: "Forward errors", tone: "text-red-400" },
  { key: "queue_overflow", label: "Queue overflow" },
];

export function MetricsCards({ stats }: { stats: Stats | null }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {CARDS.map((card) => {
        const value = stats ? (stats[card.key] as number) : null;
        return (
          <Card key={card.key} className="gap-1 px-4 py-3">
            <div className={cn("font-mono text-2xl font-semibold tabular-nums", card.tone)}>
              {value === null ? "—" : value.toLocaleString()}
            </div>
            <div className="text-[11px] tracking-wide text-muted-foreground uppercase">
              {card.label}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
