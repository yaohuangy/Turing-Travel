import axios from "axios";
import type { GenerateResponse, Itinerary, SaveRequest, TripRequest, TripSummary } from "../types";

const api = axios.create({
  baseURL: "/api",
  timeout: 120000, // 2 minutes — LLM generation can take 40-90s
});

// Attach auth token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("tt_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("tt_token");
      localStorage.removeItem("tt_username");
      localStorage.removeItem("tt_user_id");
      // Reload to show login page
      if (window.location.pathname !== "/") {
        window.location.reload();
      }
    }
    return Promise.reject(err);
  }
);

let _amapKey: string | null = null;

export async function fetchAmapKey(): Promise<string> {
  if (_amapKey) return _amapKey;
  const { data } = await api.get<{ amap_js_key: string }>("/config");
  _amapKey = data.amap_js_key;
  return _amapKey;
}

export async function generateTrip(
  request: TripRequest
): Promise<GenerateResponse> {
  const { data } = await api.post<GenerateResponse>("/trip/generate", request, {
    timeout: 180000, // 3 minutes for generate specifically (LLM + retries + map enrichment)
  });
  return data;
}

export async function saveTrip(request: SaveRequest): Promise<{ trip_id: string }> {
  const { data } = await api.post<{ trip_id: string }>("/trip/save", request);
  return data;
}

export async function listTrips(): Promise<TripSummary[]> {
  const { data } = await api.get<TripSummary[]>("/trips");
  return data;
}

export async function getTrip(tripId: string): Promise<Itinerary> {
  const { data } = await api.get<Itinerary>(`/trip/trip/${tripId}`);
  return data;
}

export async function deleteTrip(tripId: string): Promise<void> {
  await api.delete(`/trip/trip/${tripId}`);
}

export async function editTrip(
  tripId: string,
  dayIndex: number,
  editInstruction: string
): Promise<Itinerary> {
  const { data } = await api.post<Itinerary>("/trip/edit", {
    trip_id: tripId,
    day_index: dayIndex,
    edit_instruction: editInstruction,
  }, {
    timeout: 120000,
  });
  return data;
}

export function exportMarkdownUrl(tripId: string): string {
  return `/api/export/${tripId}/markdown`;
}

export function exportPdfUrl(tripId: string): string {
  return `/api/export/${tripId}/pdf`;
}

export async function exportMarkdownDirect(itinerary: Itinerary): Promise<Blob> {
  const { data } = await api.post("/export/markdown", { itinerary }, { responseType: "blob" });
  return data;
}

export async function exportPdfDirect(itinerary: Itinerary): Promise<Blob> {
  const { data } = await api.post("/export/pdf", { itinerary }, { responseType: "blob" });
  return data;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadExportedMarkdown(itinerary: Itinerary) {
  exportMarkdownDirect(itinerary).then((blob) => downloadBlob(blob, "trip.md"));
}

export function downloadExportedPdf(itinerary: Itinerary) {
  exportPdfDirect(itinerary).then((blob) => downloadBlob(blob, "trip.pdf"));
}

/** Check if an error is a timeout (axios ECONNABORTED with timeout message). */
export function isTimeoutError(err: any): boolean {
  return err?.code === "ECONNABORTED" && err?.message?.includes("timeout");
}

export default api;
