import type { VirtualMachine, VMStatus } from "@/features/cloud/data";
import type { ApiVM, VMStatusApi } from "@/lib/api";

const statusMap: Record<VMStatusApi, VMStatus> = {
  creating: "provisioning",
  running: "running",
  stopped: "stopped",
  restarting: "provisioning",
  failed: "degraded",
  deleted: "stopped",
};

const pct = (value: number, ceiling: number) =>
  Math.max(0, Math.min(100, Math.round((value / ceiling) * 100)));

function uptimeFrom(iso: string): string {
  const started = new Date(iso).getTime();
  if (Number.isNaN(started)) return "—";
  const mins = Math.max(0, Math.floor((Date.now() - started) / 60000));
  const d = Math.floor(mins / 1440);
  const h = Math.floor((mins % 1440) / 60);
  const m = mins % 60;
  if (d > 0) return `${d}d ${String(h).padStart(2, "0")}h`;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  return `${m}m`;
}

/** Maps a backend VM record onto the Phase 1 VM card view model. */
export function toVirtualMachine(vm: ApiVM): VirtualMachine {
  const stopped = vm.status === "stopped" || vm.status === "deleted";
  return {
    id: vm.id,
    name: vm.name,
    status: statusMap[vm.status] ?? "provisioning",
    cpu: stopped ? 0 : pct(vm.cpu, 8),
    ram: stopped ? 0 : pct(vm.ram, 8192),
    storage: pct(vm.storage, 100),
    os: vm.image ?? "ubuntu:22.04",
    region: vm.region ?? "local-docker",
    ip: vm.container_id ? vm.container_id.slice(0, 12) : "no container",
    uptime: stopped || vm.status === "failed" ? "—" : uptimeFrom(vm.created_at),
  };
}

export const storageLabel = (vm: ApiVM) => `${vm.storage} GB`;