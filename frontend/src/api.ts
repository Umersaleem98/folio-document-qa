export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function sessionUser<T>(): Promise<T | null> {
  try {
    return (await api<{ user: T | null }>("/auth/session")).user;
  } catch (error) {
    // Support a backend still running the previous authentication routes.
    if (!(error instanceof ApiError) || error.status !== 404) throw error;
    try {
      return await api<T>("/auth/me");
    } catch (fallbackError) {
      if (fallbackError instanceof ApiError && fallbackError.status === 401)
        return null;
      throw fallbackError;
    }
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const csrf =
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("csrf_token="))
      ?.split("=")
      .slice(1)
      .join("=") ?? "";
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  const response = await fetch("/api" + path, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    const message =
      typeof body.detail === "string"
        ? body.detail
        : "Please check the entered values.";
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
