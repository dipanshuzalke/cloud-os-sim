import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Cpu,
  HardDrive,
  MemoryStick,
  Network,
  Plus,
  Rocket,
  Scale,
  Server,
  Timer,
} from "lucide-react";
import { PageHeader } from "@/components/os/shell";
import { Counter, Reveal } from "@/components/motion/reveal";
import {
  LiveNetworkLineChart,
  LiveUsageAreaChart,
  NetworkLineChart,
  TaskDonutChart,
  UsageAreaChart,
  WeeklyBarChart,
} from "@/components/cloud/charts";
import { LiveIndicator } from "@/components/cloud/live-indicator";
import { useLiveMetrics } from "@/features/cloud/live";
import { activity } from "@/features/cloud/data";
import { VMCard } from "@/components/cloud/vm-card";
import { CreateTaskDialog, CreateVMDialog } from "@/components/cloud/create-dialogs";
import { BackendErrorState, GlassSkeletonGrid } from "@/components/cloud/states";
import { useTasks, useVMs } from "@/features/cloud/hooks";
import { toVirtualMachine, withLiveSample } from "@/features/cloud/adapters";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/os/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Cloud OS" },
      {
        name: "description",
        content: "Fleet overview with live CPU, memory, storage, network and workload telemetry.",
      },
      { property: "og:title", content: "Dashboard — Cloud OS" },
      { property: "og:description", content: "Monitor infrastructure, workloads and resource utilization." },
    ],
  }),
  component: DashboardPage,
});

const activityIcon = {
  scale: Scale,
  task: Activity,
  alert: AlertTriangle,
  scheduler: Timer,
  vm: Server,
};

function DashboardPage() {
  const live = useLiveMetrics();
  const hasLive = live.history.length > 1;
  const vmsQuery = useVMs();
  const tasksQuery = useTasks();
  const vms = vmsQuery.data ?? [];
  const tasks = tasksQuery.data ?? [];
  const loading = vmsQuery.isPending || tasksQuery.isPending;
  const failed = vmsQuery.isError && tasksQuery.isError;

  const running = vms.filter((v) => v.status === "running");
  const totalCpu = vms.reduce((a, v) => a + v.cpu, 0);
  const totalRam = vms.reduce((a, v) => a + v.ram, 0);
  const totalStorage = vms.reduce((a, v) => a + v.storage, 0);
  const queued = tasks.filter((t) => t.status === "queued").length;
  const containerised = vms.filter((v) => v.container_id).length;

  const kpis = [
    { icon: Server, label: "Running VMs", value: running.length, suffix: "", hint: `${vms.length} provisioned` },
    { icon: Cpu, label: "vCPU allocated", value: totalCpu, suffix: "", hint: "across the fleet" },
    { icon: MemoryStick, label: "Memory", value: Math.round(totalRam / 1024), suffix: " GB", hint: `${totalRam} MB allocated` },
    { icon: Activity, label: "Tasks", value: tasks.length, suffix: "", hint: `${queued} queued` },
    { icon: HardDrive, label: "Storage", value: totalStorage, suffix: " GB", hint: "requested" },
    { icon: Network, label: "Containers", value: containerised, suffix: "", hint: "backed by Docker" },
  ];

  const quickActions = [
    { icon: Plus, label: "Create VM", kind: "vm" as const },
    { icon: Timer, label: "Create Task", kind: "task" as const },
    { icon: Scale, label: "Open Scheduler", kind: "link" as const, to: "/os/scheduler" },
    { icon: BarChart3, label: "Analytics", kind: "link" as const, to: "/os/analytics" },
    { icon: Rocket, label: "Machines", kind: "link" as const, to: "/os/vms" },
  ];

  const actionClass =
    "glass-panel lift flex w-full items-center gap-3 rounded-[22px] px-5 py-5 text-left text-[15px] font-medium";

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <PageHeader
          title="Cloud Infrastructure Overview"
          subtitle="Monitor infrastructure, workloads and resource utilization."
        />
        <LiveIndicator connected={live.connected} />
      </div>

      {failed && (
        <BackendErrorState
          onRetry={() => {
            vmsQuery.refetch();
            tasksQuery.refetch();
          }}
          retrying={vmsQuery.isFetching || tasksQuery.isFetching}
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {kpis.map((k, i) => (
          <Reveal key={k.label} delay={i * 0.06}>
            <div className="glass-panel lift rounded-[26px] p-6">
              <div className="flex items-center justify-between">
                <k.icon className="size-4.5 text-primary" />
                <span className="text-[12px] text-muted-foreground">{k.hint}</span>
              </div>
              <div className="mt-6 text-[2.25rem] leading-none font-semibold tracking-tight">
                {loading ? (
                  <span className="inline-block h-8 w-20 animate-pulse rounded-full bg-muted align-middle" />
                ) : (
                  <Counter value={k.value} suffix={k.suffix} />
                )}
              </div>
              <div className="mt-2 text-[14px] text-muted-foreground">{k.label}</div>
            </div>
          </Reveal>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Reveal className="lg:col-span-2">
          <div className="glass-panel rounded-[26px] p-6">
            <div className="text-[15px] font-semibold">CPU & memory utilisation</div>
            {hasLive ? (
              <LiveUsageAreaChart data={live.history} height={250} />
            ) : (
              <UsageAreaChart height={250} />
            )}
          </div>
        </Reveal>
        <Reveal delay={0.06}>
          <div className="glass-panel h-full rounded-[26px] p-6">
            <div className="text-[15px] font-semibold">Task distribution</div>
            <TaskDonutChart height={250} />
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <div className="glass-panel rounded-[26px] p-6">
            <div className="text-[15px] font-semibold">Weekly usage</div>
            <WeeklyBarChart height={210} />
          </div>
        </Reveal>
        <Reveal delay={0.14} className="lg:col-span-2">
          <div className="glass-panel rounded-[26px] p-6">
            <div className="text-[15px] font-semibold">Network throughput</div>
            {hasLive ? (
              <LiveNetworkLineChart data={live.history} height={210} />
            ) : (
              <NetworkLineChart height={210} />
            )}
          </div>
        </Reveal>
      </div>

      <section className="space-y-4">
        <h2 className="text-[20px] font-semibold">Live infrastructure</h2>
        {vmsQuery.isPending ? (
          <GlassSkeletonGrid count={3} />
        ) : vms.length === 0 ? (
          <div className="glass-panel rounded-[26px] px-8 py-12 text-center text-[14.5px] text-muted-foreground">
            No machines provisioned yet.
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {vms.slice(0, 6).map((vm, i) => (
              <Reveal key={vm.id} delay={i * 0.05}>
                <VMCard
                  vm={withLiveSample(toVirtualMachine(vm), live.byVm[vm.id])}
                  storageLabel={`${vm.storage} GB`}
                />
              </Reveal>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-[20px] font-semibold">Quick actions</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {quickActions.map((a, i) => {
            const inner = (
              <>
                <span className="flex size-10 items-center justify-center rounded-2xl bg-primary-soft">
                  <a.icon className="size-4.5 text-primary" />
                </span>
                {a.label}
              </>
            );
            return (
              <Reveal key={a.label} delay={i * 0.05}>
                {a.kind === "vm" ? (
                  <CreateVMDialog trigger={<button className={actionClass}>{inner}</button>} />
                ) : a.kind === "task" ? (
                  <CreateTaskDialog trigger={<button className={actionClass}>{inner}</button>} />
                ) : (
                  <Link to={a.to} className={actionClass}>
                    {inner}
                  </Link>
                )}
              </Reveal>
            );
          })}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-[20px] font-semibold">Recent activity</h2>
        <div className="glass-panel rounded-[26px] p-7">
          <ol className="relative space-y-7 border-l border-border pl-7">
            {activity.map((a, i) => {
              const Icon = activityIcon[a.kind];
              return (
                <motion.li
                  key={a.title + i}
                  initial={{ opacity: 0, x: 12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: i * 0.07, ease: [0.16, 1, 0.3, 1] }}
                  className="relative"
                >
                  <span className="absolute top-0.5 -left-[43px] flex size-8 items-center justify-center rounded-full border border-glass-border bg-card">
                    <Icon className="size-3.5 text-primary" />
                  </span>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div className="text-[15px] font-medium">{a.title}</div>
                    <div className="text-[12px] text-muted-foreground">{a.time}</div>
                  </div>
                  <p className="mt-1 text-[14px] text-muted-foreground">{a.detail}</p>
                </motion.li>
              );
            })}
          </ol>
        </div>
      </section>
    </div>
  );
}