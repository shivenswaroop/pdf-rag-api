import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import {
  askQuestion,
  deleteDocument,
  getChunks,
  listDocuments,
  uploadFiles,
  type ChatResponse,
  type ChunksResponse,
  type DocumentMeta,
} from "./api";

const REFUSAL =
  "I cannot answer this question from the provided document content.";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function App() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [scopeId, setScopeId] = useState<string>("");
  const [asking, setAsking] = useState(false);
  const [chat, setChat] = useState<ChatResponse | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [inspect, setInspect] = useState<ChunksResponse | null>(null);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [activeSourceIdx, setActiveSourceIdx] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      setListError(null);
      const data = await listDocuments();
      setDocs(data);
      setSelected((prev) => {
        const ids = new Set(data.map((d) => d.document_id));
        return new Set([...prev].filter((id) => ids.has(id)));
      });
    } catch (err) {
      setListError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const allSelected = useMemo(
    () => docs.length > 0 && selected.size === docs.length,
    [docs, selected],
  );

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(docs.map((d) => d.document_id)));
  }

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf"),
    );
    if (!list.length) {
      setUploadMsg(null);
      setUploadErrors(["Please choose one or more PDF files."]);
      return;
    }

    setUploading(true);
    setUploadMsg(null);
    setUploadErrors([]);
    try {
      const result = await uploadFiles(list);
      setUploadMsg(result.message);
      const fails = result.results
        .filter((r) => !r.ok)
        .map((r) => `${r.filename ?? "file"}: ${"error" in r ? r.error : "failed"}`);
      setUploadErrors(fails);
      await refresh();
    } catch (err) {
      setUploadErrors([err instanceof Error ? err.message : String(err)]);
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteSelected() {
    if (!selected.size) return;
    if (!confirm(`Delete ${selected.size} document(s)? This cannot be undone.`)) {
      return;
    }
    const ids = [...selected];
    for (const id of ids) {
      try {
        await deleteDocument(id);
      } catch (err) {
        setListError(err instanceof Error ? err.message : String(err));
      }
    }
    if (scopeId && ids.includes(scopeId)) setScopeId("");
    if (inspect && ids.includes(inspect.document_id)) setInspect(null);
    await refresh();
  }

  async function handleDeleteOne(id: string) {
    if (!confirm("Delete this document from disk and the vector store?")) return;
    try {
      await deleteDocument(id);
      if (scopeId === id) setScopeId("");
      if (inspect?.document_id === id) setInspect(null);
      await refresh();
    } catch (err) {
      setListError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleInspect(id: string) {
    setInspectLoading(true);
    try {
      const data = await getChunks(id);
      setInspect(data);
    } catch (err) {
      setListError(err instanceof Error ? err.message : String(err));
    } finally {
      setInspectLoading(false);
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setChat(null);
    setChatError(null);
    setActiveSourceIdx(null);
    try {
      const res = await askQuestion(question.trim(), scopeId || null);
      setChat(res);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : String(err));
    } finally {
      setAsking(false);
    }
  }

  const isRefusal =
    chat?.answer?.trim() === REFUSAL ||
    (chat?.sources.length === 0 &&
      chat?.answer?.toLowerCase().includes("cannot answer"));

  return (
    <div className="app">
      <header className="brand">
        <h1>
          Docu<span>Query</span>
        </h1>
        <p>
          Upload PDFs, inspect what landed in the vector store, and ask
          questions answered only from your documents.
        </p>
      </header>

      <div className="layout">
        <section className="panel">
          <h2>Library</h2>
          <p className="lede">
            Upload one or many PDFs, then manage what is indexed for retrieval.
          </p>

          <div
            className={`dropzone${dragging ? " dragging" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              void handleFiles(e.dataTransfer.files);
            }}
          >
            <p>Drop PDFs here, or choose files for single / bulk upload.</p>
            <label className="btn btn-primary">
              {uploading ? "Uploading…" : "Choose PDFs"}
              <input
                type="file"
                accept="application/pdf,.pdf"
                multiple
                disabled={uploading}
                onChange={(e) => {
                  if (e.target.files) void handleFiles(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </div>

          {uploadMsg && <p className="status ok">{uploadMsg}</p>}
          {uploadErrors.length > 0 && (
            <ul className="upload-results status error">
              {uploadErrors.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          )}

          <div className="toolbar" style={{ marginTop: "1.1rem" }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={toggleAll}>
              {allSelected ? "Clear selection" : "Select all"}
            </button>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              disabled={!selected.size}
              onClick={() => void handleDeleteSelected()}
            >
              Delete selected ({selected.size})
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void refresh()}
            >
              Refresh
            </button>
          </div>

          {listError && <p className="status error">{listError}</p>}

          {docs.length === 0 ? (
            <p className="empty">No documents yet. Upload a sample PDF to begin.</p>
          ) : (
            <ul className="doc-list">
              {docs.map((doc) => (
                <li
                  key={doc.document_id}
                  className={`doc-item${selected.has(doc.document_id) ? " selected" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(doc.document_id)}
                    onChange={() => toggleOne(doc.document_id)}
                    aria-label={`Select ${doc.filename}`}
                  />
                  <div className="doc-meta">
                    <strong title={doc.filename}>{doc.filename}</strong>
                    <small>
                      {doc.page_count} pages · {doc.chunk_count} chunks ·{" "}
                      {formatDate(doc.uploaded_at)}
                    </small>
                  </div>
                  <div className="doc-actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={inspectLoading}
                      onClick={() => void handleInspect(doc.document_id)}
                    >
                      Inspect
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => void handleDeleteOne(doc.document_id)}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h2>Ask</h2>
          <p className="lede">
            Answers are grounded in retrieved chunks. Out-of-document questions
            are refused.
          </p>

          <form className="ask-form" onSubmit={(e) => void handleAsk(e)}>
            <label>
              Scope
              <select
                value={scopeId}
                onChange={(e) => setScopeId(e.target.value)}
              >
                <option value="">All documents</option>
                {docs.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Question
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="What are the eligibility criteria?"
                required
              />
            </label>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={asking || !docs.length}
            >
              {asking ? "Searching…" : "Ask question"}
            </button>
          </form>

          {asking && <p className="status loading">Retrieving context and generating answer…</p>}
          {chatError && <p className="status error">{chatError}</p>}

          {chat && (
            <div className={`answer-box${isRefusal ? " refusal" : ""}`}>
              <h3>Answer</h3>
              <p>{chat.answer}</p>
              {chat.sources.length > 0 && (
                <>
                  <div className="sources">
                    {chat.sources.map((s, idx) => (
                      <button
                        key={`${s.document_id}-${s.page}-${idx}`}
                        type="button"
                        className={`source-chip${activeSourceIdx === idx ? " active" : ""}`}
                        onClick={() =>
                          setActiveSourceIdx((prev) => (prev === idx ? null : idx))
                        }
                        title="Show source excerpt"
                      >
                        Page {s.page}
                        {s.filename ? ` · ${s.filename}` : ""}
                      </button>
                    ))}
                  </div>
                  {activeSourceIdx !== null && chat.sources[activeSourceIdx] && (
                    <div className="source-detail">
                      <div className="source-detail-header">
                        <strong>
                          Source — page {chat.sources[activeSourceIdx].page}
                          {chat.sources[activeSourceIdx].filename
                            ? ` · ${chat.sources[activeSourceIdx].filename}`
                            : ""}
                        </strong>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => setActiveSourceIdx(null)}
                        >
                          Close
                        </button>
                      </div>
                      <p>
                        {chat.sources[activeSourceIdx].text ||
                          chat.sources[activeSourceIdx].snippet}
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </section>
      </div>

      {inspect && (
        <>
          <div
            className="drawer-backdrop"
            onClick={() => setInspect(null)}
            aria-hidden
          />
          <aside className="drawer" role="dialog" aria-label="Vector store chunks">
            <header>
              <div>
                <h2>Vector store</h2>
                <p className="lede">
                  {inspect.filename} · {inspect.chunk_count} chunks indexed in
                  ChromaDB
                </p>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setInspect(null)}
              >
                Close
              </button>
            </header>
            {inspect.chunks.length === 0 ? (
              <p className="empty">No chunks found for this document.</p>
            ) : (
              <ul className="chunk-list">
                {inspect.chunks.map((c) => (
                  <li key={c.id} className="chunk-card">
                    <span className="page-tag">
                      Page {c.page} · chunk {c.chunk_index}
                    </span>
                    <p>{c.text}</p>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </>
      )}
    </div>
  );
}
