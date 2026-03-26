import React, { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api';

function formatSessionTime(iso) {
  if (!iso) return '';
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function readSidebarOpen() {
  try {
    return localStorage.getItem('nutritionChatSidebarOpen') !== 'false';
  } catch {
    return true;
  }
}

export default function Chatbot() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(readSidebarOpen);
  const bottomRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem('nutritionChatSidebarOpen', sidebarOpen ? 'true' : 'false');
    } catch {
      /* ignore */
    }
  }, [sidebarOpen]);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const refreshSessions = useCallback(async () => {
    const list = await api.chatbotSessions.list();
    setSessions(Array.isArray(list) ? list : []);
    return Array.isArray(list) ? list : [];
  }, []);

  const loadMessages = useCallback(async (sessionId) => {
    const data = await api.chatbotSessions.messages(sessionId);
    const rows = data.messages || [];
    setMessages(rows.map((m) => ({ role: m.role, content: m.content })));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setSessionsLoading(true);
      setError('');
      try {
        let list = await refreshSessions();
        if (cancelled) return;
        if (list.length === 0) {
          const created = await api.chatbotSessions.create();
          if (cancelled) return;
          list = await refreshSessions();
          setActiveSessionId(created.id);
          setMessages([]);
        } else {
          setActiveSessionId((prev) => {
            if (prev && list.some((s) => s.id === prev)) return prev;
            return list[0].id;
          });
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load chats');
      } finally {
        if (!cancelled) setSessionsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshSessions]);

  useEffect(() => {
    if (activeSessionId == null || sessionsLoading) return;
    let cancelled = false;
    (async () => {
      try {
        await loadMessages(activeSessionId);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load messages');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, sessionsLoading, loadMessages]);

  async function handleNewChat() {
    setError('');
    setSessionsLoading(true);
    try {
      const created = await api.chatbotSessions.create();
      await refreshSessions();
      setActiveSessionId(created.id);
      setMessages([]);
    } catch (err) {
      setError(err.message || 'Could not start a new chat');
    } finally {
      setSessionsLoading(false);
    }
  }

  async function handleSelectSession(id) {
    if (id === activeSessionId) return;
    setActiveSessionId(id);
    setMessages([]);
    setError('');
  }

  async function handleDeleteSession(id, e) {
    e.stopPropagation();
    if (!window.confirm('Delete this chat and all its messages?')) return;
    setError('');
    try {
      await api.chatbotSessions.delete(id);
      const list = await refreshSessions();
      if (list.length === 0) {
        const created = await api.chatbotSessions.create();
        await refreshSessions();
        setActiveSessionId(created.id);
        setMessages([]);
      } else if (id === activeSessionId) {
        setActiveSessionId(list[0].id);
      }
    } catch (err) {
      setError(err.message || 'Failed to delete chat');
    }
  }

  async function handleSend(e) {
    e?.preventDefault();
    if (!message.trim() || loading || activeSessionId == null) return;
    const userMsg = message.trim();
    setMessage('');
    setMessages((m) => [...m, { role: 'user', content: userMsg }]);
    setLoading(true);
    setError('');
    try {
      const { response } = await api.chatbot(userMsg, activeSessionId);
      setMessages((m) => [...m, { role: 'assistant', content: response }]);
      await refreshSessions();
    } catch (err) {
      setError(err.message || 'Failed to get response');
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content:
            "I'm here to help with nutrition and diabetes. Try: 'What foods are good for diabetes?' or 'What is the GI of matooke?'",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-content page-content--chat-fill">
      <div className="page-header">
        <h1>
          <i className="fas fa-comments" /> Nutrition Assistant
        </h1>
        <p>
          Ask about foods, blood sugar, meal ideas, or alternatives. E.g. &quot;Is matooke good for
          diabetes?&quot;
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className={`chat-layout card ${sidebarOpen ? '' : 'chat-layout--sidebar-collapsed'}`}>
        <aside className="chat-sidebar" aria-hidden={!sidebarOpen}>
          <div className="chat-sidebar-header">
            <div className="chat-sidebar-header-left">
              <button
                type="button"
                className="chat-sidebar-hide-btn"
                onClick={() => setSidebarOpen(false)}
                title="Hide chat list"
                aria-label="Hide chat list"
                aria-expanded={sidebarOpen}
              >
                <i className="fas fa-chevron-left" aria-hidden="true" />
              </button>
              <span className="chat-sidebar-title">Chats</span>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm chat-new-btn"
              onClick={handleNewChat}
              disabled={sessionsLoading}
              title="New chat"
            >
              <i className="fas fa-plus" /> New
            </button>
          </div>
          <div className="chat-session-list">
            {sessionsLoading && sessions.length === 0 ? (
              <p className="text-muted text-sm p-3 mb-0">Loading…</p>
            ) : sessions.length === 0 ? (
              <p className="text-muted text-sm p-3 mb-0">No chats yet.</p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  className={`chat-session-item ${s.id === activeSessionId ? 'active' : ''}`}
                  onClick={() => handleSelectSession(s.id)}
                  onKeyDown={(ev) => {
                    if (ev.key === 'Enter' || ev.key === ' ') {
                      ev.preventDefault();
                      handleSelectSession(s.id);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="chat-session-row">
                    <div className="chat-session-text truncate">
                      {s.title || `Chat #${s.id}`}
                    </div>
                    <button
                      type="button"
                      className="btn-icon chat-session-delete"
                      title="Delete chat"
                      aria-label="Delete chat"
                      onClick={(e) => handleDeleteSession(s.id, e)}
                    >
                      <i className="fas fa-trash-alt" />
                    </button>
                  </div>
                  <div className="chat-session-meta text-muted">
                    {formatSessionTime(s.updated_at || s.created_at)}
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        <div className="chat-main">
          {!sidebarOpen && (
            <button
              type="button"
              className="chat-sidebar-show-btn"
              onClick={() => setSidebarOpen(true)}
              title="Show chat list"
              aria-label="Show chat list"
            >
              <i className="fas fa-chevron-right" aria-hidden="true" />
              <span className="chat-sidebar-show-label">Chats</span>
            </button>
          )}
          <div className="chat-messages min-h-0 min-w-0 flex-1 overflow-y-auto p-4">
            {messages.length === 0 && !loading && (
              <p className="text-muted text-center p-5 mb-0">
                Start a conversation. Ask about nutrition, foods, or diabetes management.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={`${m.role}-${i}`}
                className={`chat-bubble ${m.role === 'user' ? 'chat-user' : 'chat-assistant'}`}
              >
                <div className="chat-content">{m.content}</div>
              </div>
            ))}
            {loading && (
              <div className="text-muted text-center p-4 mb-0">
                Thinking<span className="dots">...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={handleSend} className="p-4 border-top d-flex gap-2">
            <input
              type="text"
              className="form-input flex-1"
              placeholder="Type your question..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={loading || activeSessionId == null}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || activeSessionId == null}
            >
              <i className="fas fa-paper-plane" /> Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
