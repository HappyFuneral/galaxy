import { CONFIG } from "./config";

async function request<T>(
  path: string,
  opts: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = 120000, ...init } = opts;

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
      const msg =
        data?.error || data?.detail || `${res.status} ${res.statusText}`;
      throw new Error(msg);
    }
    return data as T;
  } finally {
    clearTimeout(t);
  }
}
async function request_new<T>(method: HttpMethod, path: string, opts?: { params?: Record<string, any>; body?: any; headers?: Record<string, string> }): Promise<T> {
  const url = new URL(CONFIG.API_BASE_URL + path);
  if (opts?.params) {
    for (const [k, v] of Object.entries(opts.params)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = { ...(opts?.headers ?? {}) };
  const init: RequestInit = { method, headers };

  if (opts?.body !== undefined && opts?.body !== null) {
    if (opts.body instanceof FormData) {
      init.body = opts.body as any;
    } else {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
  }

  const res = await fetch(url.toString(), init);
  const text = await res.text();
  if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
  try { return JSON.parse(text) as T; } catch { return (text as any) as T; }
}

export type UploadResp = { video_id: string; filename: string; path: string };
export type UploadBgmResp = { bgm_id: string; filename: string; path: string };
export type CreateJobResp = { job_id: string };

export type Job = {
  job_id: string;
  video_id: string;
  platform: string;
  export: boolean;
  status: "queued" | "running" | "done" | "failed";
  stage: string;
  progress: number;
  error: string | null;
  created_at: number;
  updated_at: number;
  captions: boolean;
  bgm_path?: string | null;
  burn_in?: boolean;
  speaker_focus?: boolean;
};

function buildQuery(params: Record<string, any>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null) return;
    sp.append(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function uploadVideo(
  uri: string,
  name = "video.mp4",
): Promise<UploadResp> {
  const form = new FormData();
  form.append("file", { uri, name, type: "video/mp4" } as any);

  return request<UploadResp>("/upload", {
    method: "POST",
    body: form as any,
    // fetch RN-nél NE add meg kézzel a multipart boundary-t:
    // headers: { "Content-Type": "multipart/form-data" }  <-- ezt NE
  });
}

export async function uploadBgm(
  uri: string,
  name = "bgm.mp3",
): Promise<UploadBgmResp> {
  const form = new FormData();
  form.append("file", { uri, name, type: "audio/mpeg" } as any);

  return request<UploadBgmResp>("/upload-bgm", {
    method: "POST",
    body: form as any,
  });
}

export async function createJob(params: {
  video_id: string;
  platform: string;
  export: boolean;
  bgm_id?: string | null;
  captions?: boolean;
  burn_in?: boolean;
  speaker_focus?: boolean;
}): Promise<CreateJobResp> {
  const qs = buildQuery(params);
  return request<CreateJobResp>(`/jobs${qs}`, { method: "POST" });
}

export async function getJob(job_id: string): Promise<Job> {
  return request<Job>(`/jobs/${job_id}`, { method: "GET" });
}

export async function getJobResult(job_id: string): Promise<any> {
  return request<any>(`/jobs/${job_id}/result`, { method: "GET" });
}

export function downloadUrl(job_id: string, filename: string): string {
  return `${CONFIG.API_BASE_URL}/jobs/${job_id}/downloads/${filename}`;
}

type HttpMethod = "GET" | "POST" | "PATCH";


export type PreviewResp = { job_id: string; export_id: string; preview_url: string; duration_s: number; };
export type ReexportResp = { job_id: string; base_export_id: string; new_export_id: string; file_url: string; recipe_url: string; };

export async function getExportRecipe(job_id: string, export_id: string): Promise<any> {
  return request_new<any>("GET", `/exports/${job_id}/${export_id}/recipe`);
}

export async function patchExportRecipe(job_id: string, export_id: string, overrides: any): Promise<any> {
  return request_new<any>("PATCH", `/exports/${job_id}/${export_id}/recipe`, { body: { overrides } });
}

export async function previewExport(job_id: string, export_id: string, body: { seconds?: number; size_w?: number; size_h?: number; overrides?: any }): Promise<PreviewResp> {
  return request_new<PreviewResp>("POST", `/exports/${job_id}/${export_id}/preview`, { body });
}

export async function reexportHQ(job_id: string, export_id: string, overrides: any): Promise<ReexportResp> {
  return request_new<ReexportResp>("POST", `/exports/${job_id}/${export_id}/reexport`, { body: { overrides } });
}

export function absoluteUrl(pathOrUrl: string): string {
  if (!pathOrUrl) return "";
  if (pathOrUrl.startsWith("http")) return pathOrUrl;
  return CONFIG.API_BASE_URL + pathOrUrl;
}
