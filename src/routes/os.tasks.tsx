import { AnimatePresence, motion } from "motion/react";
import { Plus, X } from "lucide-react";
import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/os/shell";
import { Reveal } from "@/components/motion/reveal";
import { CreateTaskDialog } from "@/components/cloud/create-dialogs";
import { BackendErrorState, EmptyState, GlassSkeletonGrid } from "@/components/cloud/states";
import { useDeleteTask, useTasks } from "@/features/cloud/hooks";
import type { TaskStatusApi } from "@/lib/api";

export const Route = createFileRoute("/os/tasks")({
  head: () => ({
    meta: [
      { title: "Tasks — Cloud OS" },
      { name: "description", content: "Running, queued, completed and failed workloads with progress, CPU, memory and estimated completion." },
      { property: "og:title", content: "Tasks — Cloud OS" },
      { property: "og:description", content: "Track simulated workloads across their full lifecycle." },
    ],
  }),
  component: TasksPage,
});

const groups: { state: TaskStatusApi; label: string; accent: string }[] = [
  { state: "running", label: "Running", accent: "bg-primary" },
  { state: "queued", label: "Queued", accent: "bg-muted-foreground" },
  { state: "completed", label: "Completed", accent: "bg-success" },
  { state: "failed", label: "Failed", accent: "bg-destructive" },
];

function TasksPage() {
  const { data: tasks, isPending, isError, error, refetch, isFetching } = useTasks();
  const remove = useDeleteTask();

  const header = (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <PageHeader
        title="Workloads"
        subtitle="Every task stored in the platform database, from dispatch to completion."
      />
      <CreateTaskDialog
        trigger={
          <button className="glass-panel lift inline-flex items-center gap-2 rounded-full px-5 py-3 text-[14px] font-medium">
            <Plus className="size-4 text-primary" /> Create Task
          </button>
        }
      />
    </div>
  );

  if (isPending) {
    return (
      <div className="space-y-10">
        {header}
        <GlassSkeletonGrid />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-10">
        {header}
        <BackendErrorState
          onRetry={() => refetch()}
          retrying={isFetching}
          message={error instanceof Error ? error.message : undefined}
        />
      </div>
    );
  }

  return (
    <div className="space-y-10">
      {header}
      {tasks.length === 0 && (
        <EmptyState
          title="No workloads queued"
          subtitle="Create a task to place it in the scheduler backlog."
        />
      )}
      {groups.map((g, gi) => {
        const items = tasks.filter((t) => t.status === g.state);
        if (items.length === 0) return null;
        return (
          <section key={g.state} className="space-y-4">
            <div className="flex items-center gap-3">
              <span className={`size-2 rounded-full ${g.accent}`} />
              <h2 className="text-[19px] font-semibold">{g.label}</h2>
              <span className="text-[13px] text-muted-foreground">{items.length}</span>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <AnimatePresence mode="popLayout">
              {items.map((t, i) => (
                <motion.div key={t.id} layout exit={{ opacity: 0, scale: 0.96, filter: "blur(6px)" }}>
                <Reveal delay={gi * 0.03 + i * 0.05}>
                  <div className="glass-panel lift h-full rounded-[26px] p-6">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-mono text-[15px] font-semibold">{t.name}</div>
                        <div className="mt-1 text-[12px] text-muted-foreground">
                          {t.id.slice(0, 8)} · {t.assigned_vm_id ? t.assigned_vm_id.slice(0, 8) : "unassigned"}
                        </div>
                      </div>
                      <button
                        onClick={() => remove.mutate(t.id)}
                        disabled={remove.isPending && remove.variables === t.id}
                        aria-label={`Delete ${t.name}`}
                        className="rounded-full border border-glass-border p-1.5 text-muted-foreground transition-colors hover:bg-muted disabled:opacity-50"
                      >
                        <X className="size-3.5" />
                      </button>
                    </div>
                    <div className="mt-6 h-1.5 rounded-full bg-muted">
                      <motion.div
                        className={`h-full rounded-full ${t.status === "failed" ? "bg-destructive" : t.status === "completed" ? "bg-success" : "bg-primary"}`}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${t.progress}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 1.2, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                    <div className="mt-4 flex justify-between text-[12.5px] text-muted-foreground">
                      <span>{t.progress}% complete</span>
                      <span>
                        {t.cpu_required} vCPU · {t.ram_required} MB
                      </span>
                    </div>
                  </div>
                </Reveal>
                </motion.div>
              ))}
              </AnimatePresence>
            </div>
          </section>
        );
      })}
    </div>
  );
}