import { useState, useEffect, useCallback, useRef } from 'react';
import {
  sendChatMessage,
  getChatSession,
  listChatSessions,
  deleteChatSession,
} from '../services/api';

const ACTIVE_SESSION_STORAGE_KEY = 'nyayasetu_active_session_id';

export function useChatSessions() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      return localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY) || null;
    } catch {
      return null;
    }
  });
  const [messages, setMessages] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [loadingStage, setLoadingStage] = useState('Searching legal sources...');
  const [error, setError] = useState(null);
  const [lastFailedQuery, setLastFailedQuery] = useState(null);

  const activeSessionRef = useRef(activeSessionId);
  useEffect(() => {
    activeSessionRef.current = activeSessionId;
  }, [activeSessionId]);

  // 1. Fetch recent sessions from MongoDB on initial mount
  const refreshSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const res = await listChatSessions(1, 50);
      if (res && res.success && Array.isArray(res.sessions)) {
        setSessions(res.sessions);
        return res.sessions;
      }
    } catch (err) {
      console.warn('[NyayaSetu] Failed to load chat sessions:', err);
    } finally {
      setLoadingSessions(false);
    }
    return [];
  }, []);

  // 2. Load messages for a specific session ID
  const loadSessionMessages = useCallback(async (sessionId) => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    setLoadingMessages(true);
    setError(null);
    try {
      const res = await getChatSession(sessionId);
      if (res && res.success) {
        const mapped = (res.messages || []).map((m) => ({
          id: m._id || m.messageId || `msg-${Date.now()}-${Math.random()}`,
          role: m.role,
          content: m.content,
          sources: m.sources || [],
          timestamp: m.createdAt
            ? new Date(m.createdAt).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: true,
              })
            : '',
        }));
        setMessages(mapped);
      } else {
        setError(res.error || 'Failed to load conversation messages.');
      }
    } catch (err) {
      setError('Unable to retrieve conversation from server.');
      console.error('[NyayaSetu] Error loading session messages:', err);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // 3. Initial mount: load sessions and restore previous active session
  useEffect(() => {
    let isMounted = true;
    (async () => {
      const loadedSessions = await refreshSessions();
      if (!isMounted) return;

      const storedId = activeSessionRef.current;
      if (storedId && loadedSessions.some((s) => s.sessionId === storedId)) {
        await loadSessionMessages(storedId);
      } else if (storedId) {
        // Stored session no longer exists in DB
        try {
          localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
        } catch {}
        setActiveSessionId(null);
        setMessages([]);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [refreshSessions, loadSessionMessages]);

  // 4. Select / Switch conversation
  const selectSession = useCallback(
    async (sessionId) => {
      if (sessionId === activeSessionId && messages.length > 0) return;
      setActiveSessionId(sessionId);
      setError(null);
      setLastFailedQuery(null);
      try {
        if (sessionId) {
          localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sessionId);
        } else {
          localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
        }
      } catch {}

      if (sessionId) {
        await loadSessionMessages(sessionId);
      } else {
        setMessages([]);
      }
    },
    [activeSessionId, messages.length, loadSessionMessages]
  );

  // 5. Start a new conversation (fresh state)
  const startNewConversation = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setError(null);
    setLastFailedQuery(null);
    try {
      localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    } catch {}
  }, []);

  // 6. Send user message with multi-stage loading & optimistic rendering
  const sendMessage = useCallback(
    async (rawText, isRetry = false) => {
      const text = rawText ? rawText.trim() : '';
      if (!text || sending) return;

      setError(null);
      setLastFailedQuery(text);
      setSending(true);
      setLoadingStage('Searching legal sources...');

      const stageTimer = setTimeout(() => {
        setLoadingStage('Preparing a source-backed response...');
      }, 2400);

      const userTime = new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });

      // Optimistic user message if not retrying an already displayed message
      if (!isRetry) {
        const userMsg = {
          id: `user-${Date.now()}`,
          role: 'user',
          content: text,
          timestamp: userTime,
          sources: [],
        };
        setMessages((prev) => [...prev, userMsg]);
      }

      try {
        const res = await sendChatMessage(text, activeSessionId);
        clearTimeout(stageTimer);

        if (res && res.success && res.message) {
          const effectiveId = res.sessionId || activeSessionId;
          if (effectiveId && effectiveId !== activeSessionId) {
            setActiveSessionId(effectiveId);
            try {
              localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, effectiveId);
            } catch {}
          }

          const asstMsg = {
            id: res.message._id || `asst-${Date.now()}`,
            role: 'assistant',
            content: res.message.content || '',
            sources: res.message.sources || [],
            timestamp: new Date().toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: true,
            }),
          };

          setMessages((prev) => [...prev, asstMsg]);
          setLastFailedQuery(null);
          // Refresh session list so new title / timestamps are updated in sidebar
          refreshSessions();
        } else {
          setError(
            res?.error ||
              'The legal answer service is temporarily unavailable. Your message has been preserved.'
          );
        }
      } catch (err) {
        clearTimeout(stageTimer);
        console.error('[NyayaSetu] Send message error:', err);
        setError(
          'A network error occurred while contacting the legal service. Please try again.'
        );
      } finally {
        setSending(false);
      }
    },
    [sending, activeSessionId, refreshSessions]
  );

  // 7. Retry last failed message (or generate answer for unanswered user query)
  const retryLastMessage = useCallback(() => {
    let queryToRetry = lastFailedQuery;
    if (!queryToRetry && messages.length > 0 && messages[messages.length - 1].role === 'user') {
      queryToRetry = messages[messages.length - 1].content;
    }
    if (!queryToRetry) return;
    sendMessage(queryToRetry, true);
  }, [lastFailedQuery, messages, sendMessage]);

  // 8. Delete conversation
  const deleteSession = useCallback(
    async (sessionId) => {
      try {
        const res = await deleteChatSession(sessionId);
        if (res && res.success) {
          setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));

          if (activeSessionId === sessionId) {
            startNewConversation();
          }
          return { success: true };
        }
        return { success: false, error: res?.error || 'Failed to delete conversation' };
      } catch (err) {
        console.error('[NyayaSetu] Error deleting session:', err);
        return { success: false, error: 'Network error deleting conversation.' };
      }
    },
    [activeSessionId, startNewConversation]
  );

  return {
    sessions,
    activeSessionId,
    messages,
    loadingSessions,
    loadingMessages,
    sending,
    loadingStage,
    error,
    lastFailedQuery,
    refreshSessions,
    selectSession,
    startNewConversation,
    sendMessage,
    retryLastMessage,
    deleteSession,
  };
}
