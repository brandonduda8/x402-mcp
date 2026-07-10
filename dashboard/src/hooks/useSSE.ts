/** SSE client with 10s-polling fallback and truthful connection status. */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionStatus, ToolEvent } from "../types/api";

const MAX_EVENTS = 200;
const POLL_INTERVAL = 10_000;
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000];

export function useSSE(baseUrl: string, demo: boolean) {
  const [events, setEvents] = useState<ToolEvent[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const retryCount = useRef(0);
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addEvents = useCallback((incoming: ToolEvent[]) => {
    setEvents((prev) => {
      const combined = [...prev, ...incoming.filter((e) => e.type !== "heartbeat")];
      return combined.slice(-MAX_EVENTS);
    });
  }, []);

  // Polling fallback
  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    setStatus("polling");
    pollRef.current = setInterval(async () => {
      try {
        const resp = await fetch(`${baseUrl}/stats`);
        if (resp.ok) {
          setStatus("polling");
        }
      } catch {
        setStatus("disconnected");
      }
    }, POLL_INTERVAL);
  }, [baseUrl]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // SSE connection
  const connect = useCallback(() => {
    if (demo) return;

    const es = new EventSource(`${baseUrl}/events`);
    esRef.current = es;

    es.onopen = () => {
      setStatus("connected");
      retryCount.current = 0;
      stopPolling();
    };

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as ToolEvent;
        if (data.type === "heartbeat") {
          // Heartbeat received — connection is alive
          setStatus("connected");
          return;
        }
        addEvents([data]);
      } catch {
        // Malformed SSE data — ignore
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      const delay =
        RECONNECT_DELAYS[
          Math.min(retryCount.current, RECONNECT_DELAYS.length - 1)
        ];
      retryCount.current++;

      // Fall back to polling while reconnecting
      startPolling();

      setTimeout(() => {
        connect();
      }, delay);
    };
  }, [baseUrl, demo, addEvents, startPolling, stopPolling]);

  useEffect(() => {
    if (demo) {
      setStatus("connected");
      return;
    }

    connect();

    return () => {
      esRef.current?.close();
      esRef.current = null;
      stopPolling();
    };
  }, [connect, demo, stopPolling]);

  return { events, status, addEvents };
}
