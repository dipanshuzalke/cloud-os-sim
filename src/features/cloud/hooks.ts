import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ApiError,
  createTask,
  createVM,
  deleteTask,
  deleteVM,
  getTasks,
  getVMs,
  restartVM,
  startVM,
  stopVM,
  type CreateTaskInput,
  type CreateVMInput,
} from "@/lib/api";

export const vmKeys = { all: ["vms"] as const };
export const taskKeys = { all: ["tasks"] as const };

export function useVMs() {
  return useQuery({ queryKey: vmKeys.all, queryFn: getVMs, refetchInterval: 15000, retry: 1 });
}

export function useTasks() {
  return useQuery({ queryKey: taskKeys.all, queryFn: getTasks, refetchInterval: 15000, retry: 1 });
}

function message(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

export function useCreateVM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateVMInput) => createVM(input),
    onSuccess: (vm) => {
      qc.invalidateQueries({ queryKey: vmKeys.all });
      toast.success(`${vm.name} provisioned`, {
        description: vm.container_id
          ? `Container ${vm.container_name}`
          : "Created as a database record (Docker not connected).",
      });
    },
    onError: (error) =>
      toast.error("Could not create the machine", {
        description: message(error, "The infrastructure service rejected the request."),
      }),
  });
}

export function useDeleteVM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteVM(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vmKeys.all });
      toast.success("Machine deleted", { description: "Container and record removed." });
    },
    onError: (error) =>
      toast.error("Delete failed", { description: message(error, "Unable to remove the machine.") }),
  });
}

export function useVMLifecycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: "start" | "stop" | "restart" }) =>
      action === "start" ? startVM(id) : action === "stop" ? stopVM(id) : restartVM(id),
    onSuccess: (vm, { action }) => {
      qc.invalidateQueries({ queryKey: vmKeys.all });
      toast.success(`${vm.name} ${action === "stop" ? "stopped" : action + "ed"}`, {
        description: `Status is now ${vm.status}.`,
      });
    },
    onError: (error) =>
      toast.error("Action failed", { description: message(error, "Docker rejected the action.") }),
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTaskInput) => createTask(input),
    onSuccess: (task) => {
      qc.invalidateQueries({ queryKey: taskKeys.all });
      toast.success(`${task.name} queued`, { description: "Workload stored in the database." });
    },
    onError: (error) =>
      toast.error("Could not create the task", {
        description: message(error, "The infrastructure service rejected the request."),
      }),
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.all });
      toast.success("Task removed");
    },
    onError: (error) =>
      toast.error("Delete failed", { description: message(error, "Unable to remove the task.") }),
  });
}