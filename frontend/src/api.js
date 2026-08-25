const RAW_URL = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");
const BACKEND_BASE = RAW_URL.endsWith("/api") ? RAW_URL.slice(0, -4) : RAW_URL;

export const API_BASE = BACKEND_BASE ? `${BACKEND_BASE}/api` : "/api";
export const UPLOADS_BASE = BACKEND_BASE ? `${BACKEND_BASE}/uploads` : "/uploads";

export function getImageUrl(imagePath) {
  if (!imagePath) return "";
  if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
    return imagePath;
  }
  const filename = imagePath.split(/[\\/]/).pop();
  return `${UPLOADS_BASE}/${filename}`;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/documents/stats/summary`);
  if (!res.ok) {
    throw new Error(`Failed to fetch stats with status ${res.status}`);
  }
  return res.json();
}

export async function fetchDocuments({ documentType, confidence, needsReview, search } = {}) {
  const params = new URLSearchParams();
  if (documentType) params.append("document_type", documentType);
  if (confidence) params.append("confidence", confidence);
  if (needsReview !== undefined && needsReview !== null) params.append("needs_review", needsReview);
  if (search) params.append("search", search);

  const res = await fetch(`${API_BASE}/documents?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch documents with status ${res.status}`);
  }
  return res.json();
}

export async function fetchDocumentById(id) {
  const res = await fetch(`${API_BASE}/documents/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch document #${id} with status ${res.status}`);
  }
  return res.json();
}

export async function uploadImages(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: `Upload failed with status ${res.status}` }));
    throw new Error(error.detail || "Upload failed");
  }
  return res.json();
}

export async function updateDocument(id, updates) {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: `Update failed with status ${res.status}` }));
    throw new Error(error.detail || `Update failed with status ${res.status}`);
  }
  return res.json();
}

export async function deleteDocument(id) {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error(`Delete failed with status ${res.status}`);
  }
  return res.json();
}

export async function reprocessDocument(id) {
  const res = await fetch(`${API_BASE}/documents/${id}/reprocess`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: `Reprocessing failed with status ${res.status}` }));
    throw new Error(error.detail || `Reprocessing failed with status ${res.status}`);
  }
  return res.json();
}

export async function askQuery({ question, documentIds = null, scope = "all", forceVision = false }) {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      scope,
      force_vision: forceVision,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: `Query failed with status ${res.status}` }));
    throw new Error(error.detail || "Query failed");
  }
  return res.json();
}

export async function loadSampleData() {
  const res = await fetch(`${API_BASE}/sample-data/load-all`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to load sample data with status ${res.status}`);
  }
  return res.json();
}
