/**
 * apiClient.js -- tiny fetch wrapper for the BVA API.
 *
 * All frontend API access goes through here, so later phases have exactly
 * one place to adjust error handling. The Vite dev proxy makes "/api/..."
 * same-origin in development -- no host configuration needed.
 */

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = network-level failure (server down)
  }
}

/** GET a JSON endpoint; resolves with the parsed body or throws ApiError. */
export async function apiGet(path) {
  let response;
  try {
    response = await fetch(path, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError(
      "Cannot reach the BVA API. Is the Flask server running in terminal 1?",
      0
    );
  }
  if (!response.ok) {
    throw new ApiError(`API request failed (${response.status})`, response.status);
  }
  return response.json();
}

/**
 * POST to a JSON endpoint. `body` may be a FormData object (file uploads --
 * leave Content-Type unset so the browser sets the multipart boundary) or a
 * plain object (sent as JSON). Resolves with the parsed JSON body, or throws
 * ApiError using the server's own `message` field when available.
 */
export async function apiPost(path, body, { asForm = false } = {}) {
  let response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: asForm ? undefined : { "Content-Type": "application/json" },
      body: asForm ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "Cannot reach the BVA API. Is the Flask server running in terminal 1?",
      0
    );
  }

  // Read the body once; it may be an error payload or the happy-path JSON.
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      payload?.message || `Request failed (HTTP ${response.status}).`,
      response.status
    );
  }
  return payload;
}
