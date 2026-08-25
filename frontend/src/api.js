const API_BASE = "/api";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/documents/stats/summary`);
  return res.json();
}

export async function fetchDocuments({ documentType, confidence, needsReview, search } = {}) {
  const params = new URLSearchParams();
  if (documentType) params.append("document_type", documentType);
  if (confidence) params.append("confidence", confidence);
  if (needsReview !== undefined && needsReview !== null) params.append("needs_review", needsReview);
  if (search) params.append("search", search);

  const res = await fetch(`${API_BASE}/documents?${params.toString()}`);
  return res.json();
}

export async function fetchDocumentById(id) {
  const res = await fetch(`${API_BASE}/documents/${id}`);
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
    const error = await res.json();
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
  return res.json();
}

export async function deleteDocument(id) {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function reprocessDocument(id) {
  const res = await fetch(`${API_BASE}/documents/${id}/reprocess`, {
    method: "POST",
  });
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
    const error = await res.json();
    throw new Error(error.detail || "Query failed");
  }
  return res.json();
}

export async function loadSampleData() {
  const res = await fetch(`${API_BASE}/sample-data/load-all`, {
    method: "POST",
  });
  return res.json();
}
