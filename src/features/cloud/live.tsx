/**
 * Phase 4 — live resource monitoring over Socket.IO.
 * The backend samples `docker stats` every second and pushes it here,
 * so charts update in real time instead of refreshing.
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import { API_URL } from "@/lib/api";

export interface LiveVMSample {
  vm_id: string;
  name: string;
  container_id: string | null;
  cpu_percent: number;
  memory_usage_mb: number;
  memory_limit_mb: number;
  memory_percent: number;
  network_rx_mb: number;
  network_tx_mb: number;
  network_rx_rate_kbps: number;
  network_tx_rate_kbps: number;
  block_read_mb: number;
  block_write_mb: number;
}

export interface LiveSample {
  recorded_at: string;
  docker: boolean;
  running_vms: number;
  cpu_percent: number;
  memory_percent: number;
  memory_usage_mb: number;
  network_rx_rate_kbps: number;
  network_tx_rate_kbps: number;
  vms: LiveVMSample[];
}

export interface LivePoint {
  t: string;
  cpu: number;
  mem: number;
  rx: number;
  tx: number;
}

interface LiveState {
  connected: boolean;
  latest: LiveSample | null;
  history: LivePoint[];
  byVm: Record<string, LiveVMSample>;
}

const MAX_POINTS = 60;

const LiveContext = createContext<LiveState>({
  connected: false,
  latest: null,
  history: [],
  byVm: {},
});

const clock = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "--:--"
    : d.toLocaleTimeString([], { minute: "2-digit", second: "2-digit" });
};

export function LiveMetricsProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [latest, setLatest] = useState<LiveSample | null>(null);
  const [history, setHistory] = useState<LivePoint[]>([]);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = io(API_URL, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      reconnectionDelay: 1500,
    });
    socketRef.current = socket;

    socket.on("connect", () => setConnected(true));
    socket.on("disconnect", () => setConnected(false));
    socket.on("connect_error", () => setConnected(false));
    socket.on("metrics", (sample: LiveSample) => {
      setLatest(sample);
      setHistory((prev) =>
        [
          ...prev,
          {
            t: clock(sample.recorded_at),
            cpu: Math.round(sample.cpu_percent),
            mem: Math.round(sample.memory_percent),
            rx: Math.round(sample.network_rx_rate_kbps),
            tx: Math.round(sample.network_tx_rate_kbps),
          },
        ].slice(-MAX_POINTS),
      );
    });

    return () => {
      socket.removeAllListeners();
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const value = useMemo<LiveState>(() => {
    const byVm: Record<string, LiveVMSample> = {};
    for (const s of latest?.vms ?? []) byVm[s.vm_id] = s;
    return { connected, latest, history, byVm };
  }, [connected, latest, history]);

  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export const useLiveMetrics = () => useContext(LiveContext);

export function useLiveVM(vmId: string): LiveVMSample | undefined {
  return useLiveMetrics().byVm[vmId];
}
