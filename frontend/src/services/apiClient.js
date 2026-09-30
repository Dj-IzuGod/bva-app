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
