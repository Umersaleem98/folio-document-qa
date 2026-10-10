import {
  createContext,
  useContext,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import {
  ArrowUpRight,
  BookOpen,
  Clock3,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Settings,
  ShieldCheck,
  UploadCloud,
  Menu,
  X,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { api, sessionUser } from "./api";
import type { User } from "./types";
import { Library, Chat, History, Profile, Admin } from "./pages";

interface Auth {
  user: User | null;
  setUser: (user: User | null) => void;
}
const AuthContext = createContext<Auth>({ user: null, setUser: () => {} });
export const useAuth = () => useContext(AuthContext);
export const Spinner = () => (
  <div className="loading" role="status">
    <span className="spinner-border spinner-border-sm" /> Loading…
  </div>
);
export const ErrorBox = ({ message }: { message: string }) =>
  message ? (
    <div className="alert alert-danger" role="alert">
      {message}
    </div>
  ) : null;
export const Retention = () => (
  <div className="retention">
    <Clock3 size={17} />
    <span>
      Chats automatically expire{" "}
      <strong>24 hours after your last message.</strong> Your documents stay in
      your library.
    </span>
  </div>
);
export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <BookOpen size={34} />
      <h3>{title}</h3>
      <div>{children}</div>
    </div>
  );
}

function AuthPage({ register = false }: { register?: boolean }) {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState("");
  if (user) return <Navigate to="/" replace />;
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    const data = new FormData(e.currentTarget);
    const body = {
      email: data.get("email"),
      password: data.get("password"),
      ...(register ? { name: data.get("name") } : {}),
    };
    try {
      if (register) {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify(body),
        });
        setSuccess("Account created. Sign in to get started.");
      } else {
        setUser(
          await api<User>("/auth/login", {
            method: "POST",
            body: JSON.stringify(body),
          }),
        );
        navigate("/");
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <section className="auth-story">
        <Link className="brand" to="/">
          <span className="brand-symbol">
            <BookOpen />
          </span>
          folio<span className="brand-dot">.</span>
        </Link>
        <div>
          <span className="eyebrow">YOUR KNOWLEDGE, CONNECTED</span>
          <h1>
            Good answers.
            <br />
            Grounded in
            <br />
            <em>your documents.</em>
          </h1>
          <p>
            Turn your PDFs into a searchable knowledge library. Ask a question,
            find the evidence, and go straight to the source.
          </p>
          <div className="auth-points">
            <span>
              <CheckCircle2 /> Private document library
            </span>
            <span>
              <CheckCircle2 /> Answers with page citations
            </span>
            <span>
              <CheckCircle2 /> Automatic 24-hour chat expiry
            </span>
          </div>
        </div>
        <small>Document intelligence, with clarity.</small>
      </section>
      <section className="auth-form">
        <div className="auth-card">
          <span className="eyebrow">WELCOME TO FOLIO</span>
          <h2>{register ? "Create your account" : "Welcome back"}</h2>
          <p>
            {register
              ? "A clearer way to work with your documents."
              : "Sign in to pick up your research."}
          </p>
          <ErrorBox message={error} />
          {success && (
            <div className="alert alert-success" role="status">
              {success} <Link to="/login">Sign in</Link>
            </div>
          )}
          <form onSubmit={submit}>
            {register && (
              <label className="form-label">
                Full name
                <input
                  name="name"
                  autoComplete="name"
                  className="form-control"
                  required
                  maxLength={100}
                />
              </label>
            )}
            <label className="form-label">
              Email address
              <input
                name="email"
                type="email"
                className="form-control"
                autoComplete="email"
                placeholder="you@example.com"
                required
              />
            </label>
            <label className="form-label">
              Password
              <input
                name="password"
                type="password"
                className="form-control"
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={register ? 12 : 1}
                maxLength={128}
              />
            </label>
            {register && (
              <small className="muted">Use at least 12 characters.</small>
            )}
            <button className="btn btn-primary w-100 mt-4" disabled={busy}>
              {busy ? "Please wait…" : register ? "Create account" : "Sign in"}{" "}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="auth-switch">
            {register ? "Already have an account?" : "New to Folio?"}{" "}
            <Link to={register ? "/login" : "/register"}>
              {register ? "Sign in" : "Create an account"}
            </Link>
          </div>
          <div className="privacy-note">
            <ShieldCheck size={16} /> Your files are accessible only to your
            account.
          </div>
        </div>
      </section>
    </div>
  );
}

function Shell() {
  const { user, setUser } = useAuth();
  const [mobile, setMobile] = useState(false);
  const [error, setError] = useState("");
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="app-layout">
      <button
        className="mobile-menu btn"
        aria-label="Toggle navigation"
        onClick={() => setMobile(!mobile)}
      >
        {mobile ? <X /> : <Menu />}
      </button>
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <Link to="/" className="brand">
          <span className="brand-symbol">
            <BookOpen size={24} />
          </span>
          folio<span className="brand-dot">.</span>
        </Link>
        <span className="nav-caption">WORKSPACE</span>
        <nav onClick={() => setMobile(false)}>
          <NavLink to="/" end>
            <LayoutDashboard size={19} /> Overview
          </NavLink>
          <NavLink to="/documents">
            <FileText size={19} /> Document library
          </NavLink>
          <NavLink to="/chat">
            <MessageSquare size={19} /> Ask your documents
          </NavLink>
          <NavLink to="/history">
            <Clock3 size={19} /> Conversation history
          </NavLink>
          <span className="nav-caption">ACCOUNT</span>
          <NavLink to="/profile">
            <Settings size={19} /> Profile & settings
          </NavLink>
          {user?.permissions.some((p) =>
            [
              "users.manage",
              "roles.manage",
              "monitor.read",
              "settings.manage",
              "audit.read",
            ].includes(p),
          ) && (
            <NavLink to="/admin">
              <ShieldCheck size={19} /> Administration
            </NavLink>
          )}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={22} />
          <strong>A private space for your knowledge</strong>
          <p>
            Your documents stay yours. Chats expire after 24 hours of
            inactivity.
          </p>
        </div>
        <div className="account">
          <span className="avatar">{user?.name.slice(0, 1).toUpperCase()}</span>
          <div>
            <strong>{user?.name}</strong>
            <small>{user?.role}</small>
          </div>
          <button className="icon-btn" onClick={logout} aria-label="Sign out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span> Document intelligence
          </span>
          <span className="private-chip">
            <span /> Private workspace
          </span>
        </header>
        <div className="page-content">
          <ErrorBox message={error} />
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/documents" element={<Library />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/history" element={<History />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        <footer>
          Folio · Answers grounded in your knowledge{" "}
          <span>Private by design</span>
        </footer>
      </main>
    </div>
  );
}

function Overview() {
  const { user } = useAuth();
  const [counts, setCounts] = useState<{
    documents: number;
    ready: number;
    chats: number;
  } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([
      api<import("./types").Document[]>("/documents"),
      api<import("./types").Conversation[]>("/conversations"),
    ])
      .then(([d, c]) => {
        if (active)
          setCounts({
            documents: d.length,
            ready: d.filter((x) => x.status === "ready").length,
            chats: c.length,
          });
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR KNOWLEDGE WORKSPACE</span>
          <h1>
            Hello, {user?.name.split(" ")[0]}
            <span className="heading-dot">.</span>
          </h1>
          <p>Make a little more sense of your documents today.</p>
        </div>
        <Link className="btn btn-primary" to="/documents">
          <UploadCloud size={18} /> Upload a PDF
        </Link>
      </div>
      <ErrorBox message={error} />
      <div className="hero-panel">
        <div>
          <span className="hero-tag">
            <span /> DOCUMENT INTELLIGENCE
          </span>
          <h2>
            From a stack of PDFs
            <br />
            to a moment of clarity.
          </h2>
          <p>
            Bring your documents together. Ask what matters.
            <br />
            Get answers you can trace back to the page.
          </p>
          <Link className="btn btn-light" to="/chat">
            Start a conversation <ArrowUpRight size={18} />
          </Link>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="paper paper-back" />
          <div className="paper paper-front">
            <FileText size={29} />
            <div className="paper-line long" />
            <div className="paper-line" />
            <div className="paper-line long" />
            <div className="paper-highlight" />
            <div className="paper-line" />
            <div className="paper-line long" />
            <span className="paper-stamp">
              <CheckCircle2 size={18} /> Source verified
            </span>
          </div>
          <span className="floating-spark">✦</span>
        </div>
      </div>
      <div className="metric-grid">
        {[
          {
            label: "Documents in your library",
            value: counts?.documents,
            icon: FileText,
            note: "Your personal knowledge base",
          },
          {
            label: "Ready to explore",
            value: counts?.ready,
            icon: CheckCircle2,
            note: "Processed and searchable",
          },
          {
            label: "Active conversations",
            value: counts?.chats,
            icon: MessageSquare,
            note: "24-hour inactivity retention",
          },
        ].map((m) => (
          <div className="metric-card" key={m.label}>
            <div>
              <span>{m.label}</span>
              <m.icon size={20} />
            </div>
            <strong>{m.value ?? "—"}</strong>
            <small>{m.note}</small>
          </div>
        ))}
      </div>
      <div className="section-heading">
        <h2>Your next discovery starts here</h2>
        <span>THREE SIMPLE STEPS</span>
      </div>
      <div className="step-grid">
        {[
          {
            n: "01",
            title: "Build your library",
            text: "Upload text-based PDFs. We extract, organize, and index the content.",
            link: "/documents",
            action: "Open library",
            icon: UploadCloud,
          },
          {
            n: "02",
            title: "Ask a better question",
            text: "Select your documents and ask a specific question about what’s inside.",
            link: "/chat",
            action: "Ask a question",
            icon: MessageSquare,
          },
          {
            n: "03",
            title: "Follow the evidence",
            text: "Explore page citations and exact excerpts behind every supported answer.",
            link: "/history",
            action: "View conversations",
            icon: BookOpen,
          },
        ].map((s) => (
          <div className="step-card" key={s.n}>
            <div>
              <s.icon size={23} />
              <span>{s.n}</span>
            </div>
            <h3>{s.title}</h3>
            <p>{s.text}</p>
            <Link to={s.link}>
              {s.action}
              <ArrowRight size={16} />
            </Link>
          </div>
        ))}
      </div>
      <Retention />
    </>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    sessionUser<User>()
      .then((session) => {
        if (active) {
          setUser(session);
          setError("");
        }
      })
      .catch((e) => {
        if (active && e.status !== 401) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    const expire = () => setUser(null);
    window.addEventListener("session-expired", expire);
    return () => {
      active = false;
      window.removeEventListener("session-expired", expire);
    };
  }, []);
  if (loading) return <Spinner />;
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {error && (
        <ErrorBox message={"Could not connect to the backend: " + error} />
      )}
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="/register" element={<AuthPage register />} />
        <Route
          path="/*"
          element={user ? <Shell /> : <Navigate to="/login" replace />}
        />
      </Routes>
    </AuthContext.Provider>
  );
}
