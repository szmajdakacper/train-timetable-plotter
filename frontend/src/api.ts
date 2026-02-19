import type { TrainsData, SheetsData, UploadResponse } from "./types";

const BASE = "/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/upload", { method: "POST", body: form });
}

export async function getSheets(): Promise<SheetsData> {
  return request<SheetsData>("/sheets");
}

export async function selectSheet(sheet: string): Promise<SheetsData> {
  return request<SheetsData>("/sheets/select", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sheet }),
  });
}

export async function getTrains(): Promise<TrainsData> {
  return request<TrainsData>("/trains");
}

export async function saveTime(body: {
  sheet: string;
  station: string;
  km: number;
  train_number: string;
  hour: number;
  minute: number;
  second?: number;
  day_offset?: number;
  stop_type?: string | null;
  propagate?: boolean;
}): Promise<TrainsData> {
  return request<TrainsData>("/edit/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function clearTime(body: {
  sheet: string;
  station: string;
  km: number;
  train_number: string;
  stop_type?: string | null;
}): Promise<TrainsData> {
  return request<TrainsData>("/edit/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function setColor(train_number: string, color: string): Promise<Record<string, string>> {
  const res = await request<{ train_colors: Record<string, string> }>("/colors", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ train_number, color }),
  });
  return res.train_colors;
}

export async function clearAllColors(): Promise<Record<string, string>> {
  const res = await request<{ train_colors: Record<string, string> }>("/colors/all", {
    method: "DELETE",
  });
  return res.train_colors;
}

export function downloadUrl(path: string): string {
  return `${BASE}/export/${path}`;
}
