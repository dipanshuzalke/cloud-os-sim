import { AnimatePresence, motion } from "motion/react";
import { Plus } from "lucide-react";
import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/os/shell";
import { Reveal } from "@/components/motion/reveal";
import { VMCard } from "@/components/cloud/vm-card";
import { CreateVMDialog } from "@/components/cloud/create-dialogs";
import { BackendErrorState, EmptyState, GlassSkeletonGrid } from "@/components/cloud/states";
import { useDeleteVM, useVMLifecycle, useVMs } from "@/features/cloud/hooks";
import { toVirtualMachine, withLiveSample } from "@/features/cloud/adapters";
import { useLiveMetrics } from "@/features/cloud/live";
import { LiveIndicator } from "@/components/cloud/live-indicator";

export const Route = createFileRoute("/os/vms")({
  head: () => ({
    meta: [
      { title: "Virtual Machines — Cloud OS" },
      { name: "description", content: "Twelve simulated virtual machines with live CPU, memory, storage, region and image details." },
      { property: "og:title", content: "Virtual Machines — Cloud OS" },
      { property: "og:description", content: "Inspect and control simulated virtual machines across five regions." },
    ],
  }),
  component: VMsPage,
});

function VMsPage() {
  const { data: vms, isPending, isError, error, refetch, isFetching } = useVMs();
  const lifecycle = useVMLifecycle();
  const remove = useDeleteVM();

  const pendingFor = (id: string): "start" | "stop" | "restart" | "delete" | null => {
    if (remove.isPending && remove.variables === id) return "delete";
    if (lifecycle.isPending && lifecycle.variables?.id === id) return lifecycle.variables.action;
    return null;
  };

  return (
    <div className="space-y-9">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <PageHeader
          title="Virtual Machines"
          subtitle="Live Docker-backed nodes with real capacity limits and lifecycle controls."
        />
        <CreateVMDialog
          trigger={
            <button className="glass-panel lift inline-flex items-center gap-2 rounded-full px-5 py-3 text-[14px] font-medium">
              <Plus className="size-4 text-primary" /> Create VM
            </button>
          }
        />
      </div>

      {isPending ? (
        <GlassSkeletonGrid />
      ) : isError ? (
        <BackendErrorState
          onRetry={() => refetch()}
          retrying={isFetching}
          message={error instanceof Error ? error.message : undefined}
        />
      ) : vms.length === 0 ? (
        <EmptyState
          title="No machines yet"
          subtitle="Provision your first container-backed virtual machine to populate the fleet."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {vms.map((vm, i) => (
              <motion.div key={vm.id} layout exit={{ opacity: 0, scale: 0.96, filter: "blur(6px)" }}>
                <Reveal delay={i * 0.04}>
                  <VMCard
                    vm={toVirtualMachine(vm)}
                    actions
                    storageLabel={`${vm.storage} GB`}
                    pendingAction={pendingFor(vm.id)}
                    onStart={() => lifecycle.mutate({ id: vm.id, action: "start" })}
                    onStop={() => lifecycle.mutate({ id: vm.id, action: "stop" })}
                    onRestart={() => lifecycle.mutate({ id: vm.id, action: "restart" })}
                    onDelete={() => remove.mutate(vm.id)}
                  />
                </Reveal>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}