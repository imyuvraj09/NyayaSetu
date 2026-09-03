/**
 * API service for communicating with the NyayaSetu Node.js Backend Gateway.
 * Provides functions for chat messaging, session lifecycle, history retrieval,
 * and service health monitoring.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api';

/**
 * Submit a legal question to the backend.
 * Uses the unified POST /api/chat endpoint.
 *
 * @param {string} message - User's legal query
 * @param {string|null} [sessionId] - Optional existing chat session ID
 * @returns {Promise<{ success: boolean, sessionId: string, message: Object, error?: string }>}
 */
export async function sendChatMessage(message, sessionId = null) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 185000);

  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        sessionId: sessionId || null,
        message,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMessage =
        data?.message ||
        data?.error ||
        `Server responded with error status ${response.status}`;
      return {
        success: false,
        error: errorMessage,
      };
    }

    return {
      success: true,
      sessionId: data.sessionId || data.data?.sessionId,
      message: data.message || data.data?.message,
      userMessage: data.userMessage || data.data?.userMessage,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      return {
        success: false,
        error: 'The AI legal analysis timed out. Please try asking a more specific question.',
      };
    }
    return {
      success: false,
      error: 'Unable to connect to NyayaSetu backend service.',
    };
  }
}

/**
 * Retrieve session metadata and full message history.
 *
 * @param {string} sessionId
 * @returns {Promise<{ success: boolean, session?: Object, messages?: Array, error?: string }>}
 */
export async function getChatSession(sessionId) {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/${sessionId}`, {
      headers: { Accept: 'application/json' },
    });

    const data = await response.json();
    if (!response.ok) {
      return {
        success: false,
        error: data.message || 'Failed to retrieve session',
      };
    }

    return {
      success: true,
      session: data.data?.session,
      messages: data.data?.messages || [],
    };
  } catch {
    return {
      success: false,
      error: 'Network error retrieving session history',
    };
  }
}

/**
 * List recent legal conversation sessions.
 *
 * @param {number} [page=1]
 * @param {number} [limit=20]
 * @returns {Promise<{ success: boolean, sessions?: Array, total?: number }>}
 */
export async function listChatSessions(page = 1, limit = 20) {
  try {
    const response = await fetch(`${API_BASE_URL}/chats?page=${page}&limit=${limit}`, {
      headers: { Accept: 'application/json' },
    });
    const data = await response.json();
    return {
      success: response.ok,
      sessions: data.data?.sessions || [],
      total: data.data?.total || 0,
    };
  } catch {
    return {
      success: false,
      sessions: [],
      total: 0,
    };
  }
}

/**
 * Delete a legal chat session and its stored messages.
 *
 * @param {string} sessionId
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
export async function deleteChatSession(sessionId) {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/${sessionId}`, {
      method: 'DELETE',
    });
    const data = await response.json();
    return { success: response.ok, error: data.message };
  } catch {
    return { success: false, error: 'Network error deleting session' };
  }
}

/**
 * Check backend health status and database connectivity.
 *
 * @returns {Promise<{ healthy: boolean, databaseConnected: boolean }>}
 */
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      headers: { Accept: 'application/json' },
    });
    const data = await response.json();
    return {
      healthy: response.ok && data.status === 'healthy',
      databaseConnected: !!data.database?.connected,
    };
  } catch {
    return { healthy: false, databaseConnected: false };
  }
}

export { API_BASE_URL };
