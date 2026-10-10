import { afterEach, expect, it, vi } from "vitest";
import { sessionUser } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("supports a previous backend without the session route", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: "Not Found" }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ id: "user" }) });
  vi.stubGlobal("fetch", fetch);
  expect(await sessionUser()).toEqual({ id: "user" });
  expect(fetch.mock.calls.map(call => call[0])).toEqual(["/api/auth/session", "/api/auth/me"]);
});

it("treats a logged-out previous backend as a normal session", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: "Not Found" }) })
    .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: "Authentication required" }) }));
  expect(await sessionUser()).toBeNull();
});
