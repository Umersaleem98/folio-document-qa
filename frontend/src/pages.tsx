import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import {
  FileText,
  UploadCloud,
  Trash2,
  ExternalLink,
  RefreshCw,
  Send,
  Plus,
  ArrowRight,
  Clock3,
  MessageSquare,
  ShieldCheck,
} from "lucide-react";
import { api } from "./api";
import { Empty, ErrorBox, Retention, Spinner, useAuth } from "./App";
import type {
  Audit,
  Conversation,
  Document,
  Limits,
  Message,
  Role,
  Stats,
  User,
} from "./types";

function Heading({
  tag,
  title,
  description,
  children,
}: {
  tag: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{tag}</span>
        <h1>
          {title}
          <span className="heading-dot">.</span>
        </h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
export function Status({ status }: { status: string }) {
  return (
    <span className={"status status-" + status}>
      <span />
      {status === "ready" ? "Ready to explore" : status}
    </span>
  );
}
const date = (value: string) => new Date(value).toLocaleString();

export function Library() {
  const [docs, setDocs] = useState<Document[]>([]),
    [limits, setLimits] = useState<Limits | null>(null),
    [aiWarning, setAiWarning] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState("");
  const input = useRef<HTMLInputElement>(null);
  async function load() {
    try {
      const [d, l, aiStatus] = await Promise.all([
        api<Document[]>("/documents"),
        api<Limits>("/limits"),
        api<{
          available: boolean | null;
          embedding_ready: boolean | null;
          chat_ready: boolean | null;
          message: string;
        }>("/ai/status"),
      ]);
      setDocs(d);
      setLimits(l);
      setAiWarning(
        aiStatus.available === false ||
          aiStatus.embedding_ready === false ||
          aiStatus.chat_ready === false
          ? aiStatus.message
          : "",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
    const id = setInterval(() => {
      void load();
    }, 5000);
    return () => clearInterval(id);
  }, []);
  async function upload(file: File) {
    setError("");
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF file.");
      return;
    }
    if (limits && file.size > limits.max_upload_mb * 1024 * 1024) {
      setError(`Maximum file size is ${limits.max_upload_mb} MB.`);
      return;
    }
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      await api("/documents", { method: "POST", body: form });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }
  async function remove(d: Document) {
    if (!confirm(`Delete “${d.name}” and conversations using it?`)) return;
    try {
      await api("/documents/" + d.id, { method: "DELETE" });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function retry(d: Document) {
    try {
      await api("/documents/" + d.id + "/retry", { method: "POST" });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        tag="YOUR SOURCES OF TRUTH"
        title="Document library"
        description="A home for your PDFs, ready for your next question."
      >
        <span className="count-chip">
          {docs.length} / {limits?.max_documents ?? "—"} documents
        </span>
      </Heading>
      <ErrorBox message={error} />
      {aiWarning && (
        <div className="alert alert-warning" role="status">
          {aiWarning}
        </div>
      )}
      <div
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!busy && e.dataTransfer.files[0])
            void upload(e.dataTransfer.files[0]);
        }}
      >
        <div className="upload-icon">
          <UploadCloud size={28} />
        </div>
        <div>
          <h3>
            {busy
              ? "Uploading your document…"
              : "Bring your knowledge into focus"}
          </h3>
          <p>Drop a PDF here, or choose a file to add to your library.</p>
          <small>
            PDF only · Up to {limits?.max_upload_mb ?? "—"} MB · Text-based
            documents
          </small>
        </div>
        <input
          ref={input}
          type="file"
          accept=".pdf,application/pdf"
          className="visually-hidden"
          aria-label="Upload PDF"
          disabled={busy}
          onChange={(e) => {
            if (e.target.files?.[0]) void upload(e.target.files[0]);
          }}
        />
        <button
          className="btn btn-primary"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          {busy ? (
            <span className="spinner-border spinner-border-sm" />
          ) : (
            <Plus size={18} />
          )}{" "}
          Choose PDF
        </button>
      </div>
      <div className="section-heading">
        <h2>
          All documents <small>({docs.length})</small>
        </h2>
        <input
          className="form-control search"
          aria-label="Search documents"
          placeholder="Search your library…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {loading ? (
        <Spinner />
      ) : docs.length === 0 ? (
        <Empty title="Your library starts with one document">
          <p>Add a PDF to turn its contents into searchable knowledge.</p>
        </Empty>
      ) : (
        <div className="table-card">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>DOCUMENT</th>
                  <th>STATUS</th>
                  <th>DETAILS</th>
                  <th>ADDED</th>
                  <th>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {docs
                  .filter((d) =>
                    d.name.toLowerCase().includes(search.toLowerCase()),
                  )
                  .map((d) => (
                    <tr key={d.id}>
                      <td>
                        <div className="document-name">
                          <span className="pdf-icon">
                            <FileText size={20} />
                          </span>
                          <div>
                            <strong>{d.name}</strong>
                            <small>
                              {(d.size / 1024 / 1024).toFixed(2)} MB · PDF
                            </small>
                            {d.error && (
                              <small className="text-danger">{d.error}</small>
                            )}
                          </div>
                        </div>
                      </td>
                      <td>
                        <Status status={d.status} />
                      </td>
                      <td className="muted">
                        {d.pages ? `${d.pages} pages` : "—"}
                      </td>
                      <td className="muted">
                        {new Date(d.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <div className="actions">
                          <a
                            className="icon-btn"
                            href={"/api/documents/" + d.id + "/file"}
                            aria-label={"Download " + d.name}
                          >
                            <ExternalLink size={17} />
                          </a>
                          {d.status === "failed" && (
                            <button
                              className="icon-btn"
                              onClick={() => void retry(d)}
                              aria-label={"Retry " + d.name}
                            >
                              <RefreshCw size={17} />
                            </button>
                          )}
                          {d.status === "ready" && (
                            <Link
                              className="icon-btn"
                              to={"/chat?document=" + d.id}
                              aria-label={"Chat with " + d.name}
                            >
                              <MessageSquare size={17} />
                            </Link>
                          )}
                          <button
                            className="icon-btn danger"
                            aria-label={"Delete " + d.name}
                            onClick={() => void remove(d)}
                          >
                            <Trash2 size={17} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className="info-note">
        <ShieldCheck size={18} /> Document processing runs in the background.
        You can start asking questions when a document is ready.
      </div>
    </>
  );
}

export function CitationList({ message }: { message: Message }) {
  return message.sources.length ? (
    <div className="citations">
      <span className="eyebrow">SOURCE EVIDENCE</span>
      {message.sources.map((s, i) => (
        <details key={i}>
          <summary>
            <span className="citation-number">{i + 1}</span>
            <FileText size={14} />
            {s.document_name}
            <span className="citation-page">Page {s.page}</span>
          </summary>
          <blockquote>{s.excerpt}</blockquote>
          <a href={"/api/documents/" + s.document_id + "/file"}>
            Download source PDF <ExternalLink size={13} />
          </a>
        </details>
      ))}
    </div>
  ) : null;
}

export function Chat() {
  const [params, setParams] = useSearchParams();
  const [docs, setDocs] = useState<Document[]>([]),
    [selected, setSelected] = useState<string[]>([]),
    [conv, setConv] = useState<Conversation | null>(null),
    [question, setQuestion] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [expired, setExpired] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const conversationId = params.get("conversation");
  useEffect(() => {
    let active = true;
    setLoading(true);
    setConv(null);
    setExpired(false);
    Promise.all([
      api<Document[]>("/documents"),
      conversationId
        ? api<Conversation>("/conversations/" + conversationId)
        : Promise.resolve(null),
    ])
      .then(([d, c]) => {
        if (!active) return;
        setDocs(d.filter((x) => x.status === "ready"));
        setConv(c);
        setSelected(
          c?.document_ids ??
            (params.get("document") ? [params.get("document")!] : []),
        );
        setError("");
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [conversationId, params.get("document")]);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [conv?.messages?.length]);
  useEffect(() => {
    if (!conv) return;
    const check = () => {
      if (Date.now() >= new Date(conv.expires_at).getTime()) {
        setExpired(true);
        setConv(null);
        setQuestion("");
        setError(
          "This conversation expired and is no longer accessible. Start a new chat.",
        );
      }
    };
    check();
    const interval = setInterval(check, 1000);
    return () => clearInterval(interval);
  }, [conv?.expires_at]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim() || busy || expired) return;
    setError("");
    setBusy(true);
    try {
      let current = conv;
      if (!current) {
        current = await api<Conversation>("/conversations", {
          method: "POST",
          body: JSON.stringify({
            document_ids: selected,
            title: "Document conversation",
          }),
        });
        setConv({ ...current, messages: [] });
      }
      const result = await api<{ messages: Message[]; expires_at: string }>(
        "/conversations/" + current.id + "/messages",
        { method: "POST", body: JSON.stringify({ content: question }) },
      );
      setConv({
        ...current,
        messages: [...(current.messages ?? []), ...result.messages],
        expires_at: result.expires_at,
      });
      setQuestion("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function reset() {
    setParams({});
    setConv(null);
    setSelected([]);
    setExpired(false);
    setError("");
  }
  return (
    <>
      <Heading
        tag="ASK. EXPLORE. UNDERSTAND."
        title="Ask your documents"
        description="Find a grounded answer, with the evidence right beside it."
      >
        <button
          className="btn btn-outline-secondary"
          onClick={reset}
          disabled={busy}
        >
          <Plus size={17} /> New conversation
        </button>
      </Heading>
      <ErrorBox message={error} />
      <Retention />
      {loading ? (
        <Spinner />
      ) : (
        <div className="chat-layout">
          <aside className="source-panel">
            <span className="eyebrow">CONTEXT LIBRARY</span>
            <h3>Your sources</h3>
            <p>Choose up to 10 ready documents for this conversation.</p>
            {docs.length === 0 ? (
              <p className="muted">
                No ready documents. <Link to="/documents">Upload a PDF</Link>{" "}
                first.
              </p>
            ) : (
              docs.map((d) => (
                <label
                  className={
                    "source-option " +
                    (selected.includes(d.id) ? "selected" : "")
                  }
                  key={d.id}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(d.id)}
                    disabled={
                      !!conv ||
                      busy ||
                      (!selected.includes(d.id) && selected.length >= 10)
                    }
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, d.id]
                          : selected.filter((x) => x !== d.id),
                      )
                    }
                  />
                  <FileText size={18} />
                  <span>
                    {d.name}
                    <small>{d.pages} pages</small>
                  </span>
                </label>
              ))
            )}
            <div className="source-tip">
              <ShieldCheck size={20} />
              <p>
                Answers use exact, verified excerpts. If the evidence is
                missing, Folio will say so.
              </p>
            </div>
          </aside>
          <section className="chat-panel">
            <div className="chat-panel-header">
              <span>
                <span className="green-dot" />{" "}
                {conv ? "Document conversation" : "A fresh perspective"}
              </span>
              <small>
                {selected.length} source{selected.length === 1 ? "" : "s"}{" "}
                selected
              </small>
            </div>
            <div className="message-list">
              {!conv?.messages?.length ? (
                <div className="chat-empty">
                  <span className="chat-emblem">
                    <BookOpenIcon />
                  </span>
                  <h2>What would you like to know?</h2>
                  <p>
                    Select your documents, then ask a specific question.
                    <br />
                    Every supported answer comes with its source.
                  </p>
                  <div className="question-ideas">
                    <button
                      onClick={() =>
                        setQuestion(
                          "What are the main findings in these documents?",
                        )
                      }
                    >
                      What are the main findings? <ArrowRight size={15} />
                    </button>
                    <button
                      onClick={() =>
                        setQuestion(
                          "What deadlines are mentioned in these documents?",
                        )
                      }
                    >
                      Which deadlines are mentioned? <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              ) : (
                conv.messages.map((m) => (
                  <article className={"message message-" + m.role} key={m.id}>
                    <div className="message-label">
                      {m.role === "user" ? "YOU" : "FOLIO"}
                      <time>
                        {new Date(m.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </time>
                    </div>
                    <div className="message-content">{m.content}</div>
                    <CitationList message={m} />
                  </article>
                ))
              )}
              {busy && (
                <div className="thinking" role="status">
                  <span className="spinner-border spinner-border-sm" /> Finding
                  relevant evidence…
                </div>
              )}
              <div ref={bottom} />
            </div>
            <form className="composer" onSubmit={submit}>
              <label htmlFor="question" className="visually-hidden">
                Your document question
              </label>
              <textarea
                id="question"
                placeholder="Ask a question about your selected documents…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                maxLength={2000}
                disabled={busy || expired}
                required
                rows={2}
              />
              <button
                className="btn btn-primary send"
                disabled={
                  busy || expired || !selected.length || !question.trim()
                }
                aria-label="Send question"
              >
                <Send size={19} />
              </button>
              <small>
                Grounded in your documents. Always check source evidence.{" "}
                {conv && <>Expires {date(conv.expires_at)}.</>}
              </small>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
function BookOpenIcon() {
  return <FileText size={30} />;
}

export function History() {
  const [items, setItems] = useState<Conversation[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  async function load() {
    try {
      setItems(await api<Conversation[]>("/conversations"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => clearInterval(id);
  }, []);
  async function remove(c: Conversation) {
    if (!confirm("Delete this conversation?")) return;
    try {
      await api("/conversations/" + c.id, { method: "DELETE" });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        tag="CONTINUE YOUR EXPLORATION"
        title="Conversation history"
        description="Your recent questions, and the evidence you discovered."
      >
        <Link className="btn btn-primary" to="/chat">
          <Plus size={17} /> New conversation
        </Link>
      </Heading>
      <Retention />
      <ErrorBox message={error} />
      {loading ? (
        <Spinner />
      ) : items.length === 0 ? (
        <Empty title="A clean slate">
          <p>
            Your active conversations will appear here. Chats expire after 24
            hours of inactivity.
          </p>
          <Link to="/chat" className="btn btn-primary">
            Start exploring <ArrowRight size={16} />
          </Link>
        </Empty>
      ) : (
        <div className="history-list">
          {items
            .filter((c) => new Date(c.expires_at).getTime() > Date.now())
            .map((c) => (
              <div className="history-card" key={c.id}>
                <span className="history-icon">
                  <MessageSquare size={23} />
                </span>
                <div>
                  <Link to={"/chat?conversation=" + c.id}>
                    <h3>{c.title}</h3>
                  </Link>
                  <p>
                    {c.document_ids.length} documents · Last activity{" "}
                    {date(c.last_activity_at)}
                  </p>
                  <small>
                    <Clock3 size={13} /> Expires {date(c.expires_at)}
                  </small>
                </div>
                <Link
                  className="icon-btn"
                  to={"/chat?conversation=" + c.id}
                  aria-label="Open conversation"
                >
                  <ArrowRight size={20} />
                </Link>
                <button
                  className="icon-btn danger"
                  onClick={() => void remove(c)}
                  aria-label="Delete conversation"
                >
                  <Trash2 size={17} />
                </button>
              </div>
            ))}
        </div>
      )}
    </>
  );
}

export function Profile() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(e.currentTarget);
    try {
      setUser(
        await api<User>("/profile", {
          method: "PATCH",
          body: JSON.stringify({ name: data.get("name") }),
        }),
      );
      setSuccess("Profile updated.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function password(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(e.currentTarget);
    if (data.get("new_password") !== data.get("confirmation")) {
      setError("Passwords do not match.");
      setBusy(false);
      return;
    }
    try {
      await api("/profile/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: data.get("current_password"),
          new_password: data.get("new_password"),
        }),
      });
      setUser(null);
      navigate("/login");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        tag="MAKE YOURSELF AT HOME"
        title="Profile & settings"
        description="Manage your account and keep your workspace secure."
      />
      <ErrorBox message={error} />
      {success && (
        <div className="alert alert-success" role="status">
          {success}
        </div>
      )}
      <div className="settings-grid">
        <section className="panel">
          <h2>Personal details</h2>
          <p className="muted">Your identity in this workspace.</p>
          <form onSubmit={save}>
            <label className="form-label">
              Full name
              <input
                name="name"
                className="form-control"
                defaultValue={user?.name}
                required
                maxLength={100}
              />
            </label>
            <label className="form-label">
              Email address
              <input
                className="form-control"
                value={user?.email ?? ""}
                disabled
              />
            </label>
            <p className="muted">Role: {user?.role}</p>
            <button className="btn btn-primary" disabled={busy}>
              Save changes
            </button>
          </form>
        </section>
        <section className="panel">
          <h2>Change password</h2>
          <p className="muted">
            Changing your password signs out all active sessions.
          </p>
          <form onSubmit={password}>
            <label className="form-label">
              Current password
              <input
                className="form-control"
                name="current_password"
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
              />
            </label>
            <label className="form-label">
              New password
              <input
                className="form-control"
                name="new_password"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={128}
              />
            </label>
            <label className="form-label">
              Confirm new password
              <input
                className="form-control"
                name="confirmation"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={128}
              />
            </label>
            <button className="btn btn-outline-secondary" disabled={busy}>
              Update password
            </button>
          </form>
        </section>
      </div>
      <Retention />
    </>
  );
}

export function Admin() {
  const { user } = useAuth();
  const can = (p: string) => user?.permissions.includes(p);
  const [users, setUsers] = useState<User[]>([]),
    [roles, setRoles] = useState<Role[]>([]),
    [permissions, setPermissions] = useState<string[]>([]),
    [stats, setStats] = useState<Stats | null>(null),
    [logs, setLogs] = useState<Audit[]>([]),
    [limits, setLimits] = useState<Limits | null>(null),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [newPermissions, setNewPermissions] = useState<string[]>([]);
  async function load() {
    try {
      const result = await Promise.all([
        can("users.manage") ? api<User[]>("/admin/users") : Promise.resolve([]),
        can("roles.manage")
          ? api<{ roles: Role[]; permissions: string[] }>("/admin/roles")
          : Promise.resolve({ roles: [], permissions: [] }),
        can("monitor.read")
          ? api<Stats>("/admin/stats")
          : Promise.resolve(null),
        can("audit.read") ? api<Audit[]>("/admin/audit") : Promise.resolve([]),
        api<Limits>("/limits"),
      ]);
      setUsers(result[0]);
      setRoles(result[1].roles);
      setPermissions(result[1].permissions);
      setStats(result[2]);
      setLogs(result[3]);
      setLimits(result[4]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  if (
    !user?.permissions.some((p) =>
      [
        "users.manage",
        "roles.manage",
        "monitor.read",
        "settings.manage",
        "audit.read",
      ].includes(p),
    )
  )
    return <ErrorBox message="You do not have administration permissions." />;
  async function updateUser(target: User, active: boolean, role_id: number) {
    setError("");
    setBusy(true);
    try {
      await api("/admin/users/" + target.id, {
        method: "PATCH",
        body: JSON.stringify({ active, role_id }),
      });
      await load();
      setSuccess("User updated. Their active sessions were revoked.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function saveLimits(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(e.currentTarget);
    try {
      await api("/admin/limits", {
        method: "PUT",
        body: JSON.stringify({
          max_upload_mb: Number(data.get("max_upload_mb")),
          max_documents: Number(data.get("max_documents")),
          daily_questions: Number(data.get("daily_questions")),
        }),
      });
      setSuccess("Limits updated.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function newRole(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const form = e.currentTarget;
    try {
      await api("/admin/roles", {
        method: "POST",
        body: JSON.stringify({
          name: new FormData(form).get("name"),
          permissions: newPermissions,
        }),
      });
      form.reset();
      setNewPermissions([]);
      await load();
      setSuccess("Role created.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function togglePermission(role: Role, p: string) {
    try {
      await api("/admin/roles/" + role.id, {
        method: "PUT",
        body: JSON.stringify({
          permissions: role.permissions.includes(p)
            ? role.permissions.filter((x) => x !== p)
            : [...role.permissions, p],
        }),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        tag="WORKSPACE OPERATIONS"
        title="Administration"
        description="Manage access, usage limits, and system activity."
      >
        <button
          className="btn btn-outline-secondary"
          onClick={() => void load()}
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </Heading>
      <ErrorBox message={error} />
      {success && (
        <div className="alert alert-success" role="status">
          {success}
        </div>
      )}
      {loading ? (
        <Spinner />
      ) : (
        <>
          {stats && (
            <>
              <div className="metric-grid admin-metrics">
                {[
                  { name: "Registered users", value: stats.users },
                  { name: "Documents", value: stats.documents },
                  {
                    name: "Active conversations",
                    value: stats.active_conversations,
                  },
                  {
                    name: "Questions today (UTC)",
                    value: stats.questions_today,
                  },
                ].map((s) => (
                  <div className="metric-card" key={s.name}>
                    <span>{s.name}</span>
                    <strong>{s.value}</strong>
                  </div>
                ))}
              </div>
            </>
          )}
          {can("users.manage") && (
            <section className="panel">
              <h2>User access</h2>
              <p className="muted">
                Showing the most recent 100 accounts. Role changes and
                suspensions invalidate sessions.
              </p>
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id}>
                        <td>
                          <strong>{u.name}</strong>
                          <small className="d-block muted">{u.email}</small>
                        </td>
                        <td>
                          {can("roles.manage") ? (
                            <select
                              className="form-select"
                              aria-label={"Role for " + u.email}
                              value={u.role_id}
                              disabled={busy || u.id === user.id}
                              onChange={(e) =>
                                void updateUser(
                                  u,
                                  u.active,
                                  Number(e.target.value),
                                )
                              }
                            >
                              {roles.map((r) => (
                                <option key={r.id} value={r.id}>
                                  {r.name}
                                </option>
                              ))}
                            </select>
                          ) : (
                            u.role
                          )}
                        </td>
                        <td>
                          <span
                            className={
                              "status " +
                              (u.active ? "status-ready" : "status-failed")
                            }
                          >
                            {u.active ? "Active" : "Suspended"}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            disabled={busy || u.id === user.id}
                            onClick={() =>
                              void updateUser(u, !u.active, u.role_id)
                            }
                          >
                            {u.active ? "Suspend" : "Activate"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          <div className="settings-grid">
            {can("settings.manage") && limits && (
              <section className="panel">
                <h2>Upload & AI limits</h2>
                <form onSubmit={saveLimits}>
                  <label className="form-label">
                    Maximum PDF size (MB)
                    <input
                      type="number"
                      name="max_upload_mb"
                      className="form-control"
                      defaultValue={limits.max_upload_mb}
                      min={1}
                      max={100}
                      required
                    />
                  </label>
                  <label className="form-label">
                    Documents per account
                    <input
                      type="number"
                      name="max_documents"
                      className="form-control"
                      defaultValue={limits.max_documents}
                      min={1}
                      max={1000}
                      required
                    />
                  </label>
                  <label className="form-label">
                    Daily questions per account (UTC)
                    <input
                      type="number"
                      name="daily_questions"
                      className="form-control"
                      defaultValue={limits.daily_questions}
                      min={1}
                      max={10000}
                      required
                    />
                  </label>
                  <button className="btn btn-primary" disabled={busy}>
                    Save limits
                  </button>
                </form>
              </section>
            )}
            {can("roles.manage") && (
              <section className="panel">
                <h2>Create a role</h2>
                <form onSubmit={newRole}>
                  <label className="form-label">
                    Role name
                    <input
                      name="name"
                      className="form-control"
                      required
                      minLength={2}
                      maxLength={40}
                      pattern="[a-z][a-z0-9_-]+"
                      placeholder="researcher"
                    />
                  </label>
                  <div className="permission-list">
                    {permissions.map((p) => (
                      <label key={p}>
                        <input
                          type="checkbox"
                          checked={newPermissions.includes(p)}
                          onChange={(e) =>
                            setNewPermissions(
                              e.target.checked
                                ? [...newPermissions, p]
                                : newPermissions.filter((x) => x !== p),
                            )
                          }
                        />{" "}
                        {p}
                      </label>
                    ))}
                  </div>
                  <button className="btn btn-primary mt-3" disabled={busy}>
                    Create role
                  </button>
                </form>
              </section>
            )}
          </div>
          {can("roles.manage") && (
            <section className="panel">
              <h2>Role permissions</h2>
              <p className="muted">
                Built-in roles are protected. Custom role changes apply to the
                next API request.
              </p>
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Role</th>
                      {permissions.map((p) => (
                        <th key={p}>{p}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {roles.map((r) => (
                      <tr key={r.id}>
                        <td>{r.name}</td>
                        {permissions.map((p) => (
                          <td key={p}>
                            <input
                              type="checkbox"
                              aria-label={r.name + " " + p}
                              checked={r.permissions.includes(p)}
                              disabled={["admin", "user"].includes(r.name)}
                              onChange={() => void togglePermission(r, p)}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          {stats && (
            <section className="panel">
              <h2>Document processing</h2>
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Document ID</th>
                      <th>Status</th>
                      <th>Pages</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.processing.map((d) => (
                      <tr key={d.id}>
                        <td>
                          <code>{d.id}</code>
                        </td>
                        <td>
                          <Status status={d.status} />
                        </td>
                        <td>{d.pages}</td>
                        <td>{d.error ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!stats.processing.length && (
                  <p className="muted">No processing activity yet.</p>
                )}
              </div>
            </section>
          )}
          {can("audit.read") && (
            <section className="panel">
              <h2>Security audit trail</h2>
              <p className="muted">
                Latest 100 events. Audit records contain identifiers and
                actions, without private document or chat content.
              </p>
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Actor ID</th>
                      <th>Target ID</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((a) => (
                      <tr key={a.id}>
                        <td>{date(a.created_at)}</td>
                        <td>{a.action}</td>
                        <td>
                          <code>{a.actor_id ?? "Anonymous"}</code>
                        </td>
                        <td>
                          <code>{a.target_id ?? "—"}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </>
  );
}
