/**
 * Centralised client for the FastAPI Cloud OS backend.
 * Base URL comes from VITE_API_URL — never hardcode a production host.
 */

export const API_URL: string =
  (import.meta.env["VITE_API_URL"] as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type VMStatusApi =
  | "creating"
  | "running"
  | "stopped"
  | "restarting"
  | "failed"
  | "deleted";

export interface ApiVM {
  id: string;
  name: string;
  cpu: number;
  ram: number;
  storage: number;
  status: VMStatusApi;
  image: string | null;
  region: string | null;
  container_id: string | null;
  container_name: string | null;
  volume_name: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiVMStats {
  container_id: string | null;
  container_name: string | null;
  container_status: string | null;
  cpu_limit: number | null;
  memory_limit_mb: number | null;
  cpu_percent: number | null;
  memory_usage_mb: number | null;
}

export type TaskStatusApi = "queued" | "running" | "completed" | "failed";

export interface ApiTask {
  id: string;
  name: string;
  cpu_required: number;
  ram_required: number;
  status: TaskStatusApi;
  progress: number;
  execution_time: number | null;
  assigned_vm_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateVMInput {
  name: string;
  cpu: number;
  ram: number;
  storage: number;
}

export interface CreateTaskInput {
  name: string;
  cpu_required: number;
  ram_required: number;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError("Unable to reach the infrastructure service.", 0);
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = "Invalid input. Please check the values.";
    } catch {
      /* keep default */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const getVMs = () => request<ApiVM[]>("/api/vms");
export const getVM = (id: string) => request<ApiVM>(`/api/vms/${id}`);
export const getVMStats = (id: string) => request<ApiVMStats>(`/api/vms/${id}/stats`);
export const createVM = (input: CreateVMInput) =>
  request<ApiVM>("/api/vms", { method: "POST", body: JSON.stringify(input) });
export const deleteVM = (id: string) => request<void>(`/api/vms/${id}`, { method: "DELETE" });
export const startVM = (id: string) => request<ApiVM>(`/api/vms/${id}/start`, { method: "POST" });
export const stopVM = (id: string) => request<ApiVM>(`/api/vms/${id}/stop`, { method: "POST" });
export const restartVM = (id: string) =>
  request<ApiVM>(`/api/vms/${id}/restart`, { method: "POST" });

export const getTasks = () => request<ApiTask[]>("/api/tasks");
export const getTask = (id: string) => request<ApiTask>(`/api/tasks/${id}`);
export const createTask = (input: CreateTaskInput) =>
  request<ApiTask>("/api/tasks", { method: "POST", body: JSON.stringify(input) });
export const deleteTask = (id: string) => request<void>(`/api/tasks/${id}`, { method: "DELETE" });