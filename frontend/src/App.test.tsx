import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import App, { Retention } from "./App";
import { CitationList, Status } from "./pages";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ user: null }),
      }),
  );
});
describe("Authentication and document interface", () => {
  it("protects private pages and displays sign in", async () => {
    render(
      <MemoryRouter initialEntries={["/documents"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { name: "Welcome back" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Document library")).not.toBeInTheDocument();
  });
  it("registration never submits a role", async () => {
    const calls: { path: string; body?: string }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string, options: RequestInit) => {
        calls.push({ path, body: options.body as string });
        return path.endsWith("/register")
          ? {
              ok: true,
              status: 201,
              json: async () => ({ message: "Created" }),
            }
          : {
              ok: true,
              status: 200,
              json: async () => ({ user: null }),
            };
      }),
    );
    render(
      <MemoryRouter initialEntries={["/register"]}>
        <App />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Create your account" });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Full name"), "Researcher");
    await user.type(screen.getByLabelText("Email address"), "one@example.com");
    await user.type(screen.getByLabelText("Password"), "StrongPassword123!");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() =>
      expect(calls.some((c) => c.path.endsWith("/register"))).toBe(true),
    );
    const body = JSON.parse(
      calls.find((c) => c.path.endsWith("/register"))!.body!,
    );
    expect(Object.keys(body).sort()).toEqual(["email", "name", "password"]);
  });
  it("communicates inactivity retention", () => {
    render(<Retention />);
    expect(
      screen.getByText(/24 hours after your last message/),
    ).toBeInTheDocument();
  });
  it("shows source filename, page and exact evidence as text", () => {
    render(
      <CitationList
        message={{
          id: "m",
          role: "assistant",
          content: "Answer",
          created_at: "2026-01-01T00:00:00Z",
          sources: [
            {
              document_id: "d",
              document_name: "Research.pdf",
              page: 3,
              excerpt: "<script>alert(1)</script>",
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("Research.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 3")).toBeInTheDocument();
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
  it("displays processing state", () => {
    render(<Status status="processing" />);
    expect(screen.getByText("processing")).toBeInTheDocument();
  });
});
