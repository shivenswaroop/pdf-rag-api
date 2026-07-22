export type DocumentMeta = {
  document_id: string;
  filename: string;
  path: string;
  page_count: number;
  chunk_count: number;
  uploaded_at: string;
};

export type Source = {
  page: number;
  document_id: string;
  filename?: string | null;
  text?: string;
  snippet: string;
};

export type ChatResponse = {
  answer: string;
  sources: Source[];
};

export type ChunkInfo = {
  id: string;
  page: number;
  chunk_index: number;
  text: string;
  snippet?: string;
};

export type ChunksResponse = {
  document_id: string;
  filename: string;
  chunk_count: number;
  chunks: ChunkInfo[];
};

export type UploadResult = {
  document_id: string;
  message: string;
  filename: string;
  path: string;
  page_count: number;
  chunk_count: number;
  uploaded_at: string;
};

export type BulkUploadResponse = {
  message: string;
  results: Array<
    | ({ ok: true } & UploadResult)
    | { ok: false; filename: string | null; error: string }
  >;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
    }
    return JSON.stringify(data);
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

export async function listDocuments(): Promise<DocumentMeta[]> {
  const res = await fetch(`${API_BASE}/documents/`);
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.documents ?? [];
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function getChunks(documentId: string): Promise<ChunksResponse> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/chunks`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function uploadFiles(files: File[]): Promise<BulkUploadResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  const res = await fetch(`${API_BASE}/upload/bulk/`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function askQuestion(
  question: string,
  documentId?: string | null,
): Promise<ChatResponse> {
  const body: { question: string; document_id?: string } = { question };
  if (documentId) body.document_id = documentId;

  const res = await fetch(`${API_BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export { API_BASE };
