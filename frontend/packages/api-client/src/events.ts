import { DEFAULT_API_BASE } from "./client";
import type { EventRecord } from "./types";

export interface EventStreamHandlers {
  onDecision: (record: EventRecord) => void;
  onOpen?: () => void;
  onError?: () => void;
}

export function subscribeToEvents(
  handlers: EventStreamHandlers,
  baseUrl: string = DEFAULT_API_BASE,
): EventSource {
  const base = baseUrl.replace(/\/$/, "");
  const source = new EventSource(`${base}/api/events/stream`);

  source.addEventListener("decision", (event) => {
    try {
      handlers.onDecision(JSON.parse((event as MessageEvent).data) as EventRecord);
    } catch {
      // ignore a malformed frame rather than tearing down the stream
    }
  });

  if (handlers.onOpen) {
    source.onopen = () => handlers.onOpen?.();
  }
  source.onerror = () => handlers.onError?.();

  return source;
}
