/**
 * The learner's session.
 *
 * Guest-first: on first load we ask the API for a guest session and keep the
 * token. Nobody is asked for an email before they have seen whether this is any
 * use to them — and for someone deciding whether to trust us with a disability
 * disclosure, that ordering matters.
 *
 * The token lives in localStorage. That is a real trade: it is readable by any
 * script on the origin, so an XSS becomes a session theft. The alternative — an
 * httpOnly cookie — needs a same-site deployment we do not have yet (the client
 * is on Cloudflare Pages, the API on Render), and it breaks the offline-first
 * story in M15 where the client must hold its own identity while disconnected.
 * Revisit when both live behind one domain; tracked in docs/STATUS.md.
 */

const TOKEN_KEY = 'samvaad.token';
const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface Session {
  token: string;
  userId: string;
  isGuest: boolean;
  needsOnboarding: boolean;
  /**
   * Decides which tabs are rendered, nothing more. The API refuses trainer
   * routes on the token's own claim, so a client that lied about this would
   * simply show a tab that 403s.
   */
  isTrainer: boolean;
  /** Same caveat as `isTrainer`: presentation, not a security boundary. */
  isInstitution: boolean;
}

function read(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    // Private browsing, or storage disabled. The learner still gets a working
    // session for this page load; it simply will not survive a reload.
    return null;
  }
}

function write(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* see read() */
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* see read() */
  }
}

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/**
 * Resume the stored session, or start a guest one.
 *
 * Returns null only when the API is unreachable. The caller must then tell the
 * learner plainly rather than showing an empty screen.
 */
export async function startSession(): Promise<Session | null> {
  const existing = read();

  if (existing) {
    const resumed = await request('/auth/me', 'GET', existing);
    if (resumed) return toSession(resumed);
    // A token that no longer works — expired, or the learner erased their
    // account. Drop it and start fresh rather than leaving them stuck on a
    // screen that 401s forever.
    clearSession();
  }

  const created = await request('/auth/guest', 'POST', null);
  if (!created) return null;

  write(created.access_token);
  return toSession(created);
}

interface TokenResponse {
  access_token: string;
  user_id: string;
  is_guest: boolean;
  role: string;
  needs_onboarding: boolean;
}

function toSession(body: TokenResponse): Session {
  // The API reissues on every /auth/me, so the stored token stays fresh and a
  // learner is never signed out mid-interview.
  write(body.access_token);
  return {
    token: body.access_token,
    userId: body.user_id,
    isGuest: body.is_guest,
    needsOnboarding: body.needs_onboarding,
    isTrainer: body.role === 'trainer' || body.role === 'admin',
    isInstitution: body.role === 'institution' || body.role === 'admin',
  };
}

async function request(
  path: string,
  method: 'GET' | 'POST',
  token: string | null,
): Promise<TokenResponse | null> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? authHeaders(token) : {}),
      },
    });
    return response.ok ? ((await response.json()) as TokenResponse) : null;
  } catch {
    return null;
  }
}
