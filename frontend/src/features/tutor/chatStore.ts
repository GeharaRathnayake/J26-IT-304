/** Saved chats: a refresh keeps the conversation, and "Recent" lists the student's real chats.
 *
 * PRIVACY: chats are stored only in this browser's localStorage, on the student's own device.
 * Nothing new is sent to the backend (it is stateless; the frontend already holds everything a
 * conversation needs), and none of this is research data. On a shared machine the next user of
 * the same browser can see these chats; "New chat" does not delete them, and there is no
 * clear-history control in PP1.
 *
 * A chat's id is the id of its FIRST message (a UUID from SEND_STARTED). A topic change, a reset
 * or "New chat" clears the messages, so the next message starts a new id and the old chat stays
 * in the list untouched; reopening an old chat restores its messages and so keeps its id. */
import type { EpisodeUI } from './reducer';

export const CHAT_STORE_KEY = 'java-tutor.chats.v1';
export const MAX_CHATS = 20;
const TITLE_LENGTH = 40;

export interface StoredChat { id: string; title: string; topic: string | null; updatedAt: string; state: EpisodeUI }
export interface ChatStore { version: 1; chats: StoredChat[] }

export function emptyStore(): ChatStore { return { version: 1, chats: [] }; }

/** The chat an episode state belongs to, or null while it has no message yet. */
export function chatIdFor(state: EpisodeUI): string | null { return state.messages[0]?.id ?? null; }

export function titleFor(state: EpisodeUI): string {
  const first = state.messages.find((m) => m.role === 'student')?.text.trim().replace(/\s+/g, ' ');
  if (!first) return 'New chat';
  return first.length > TITLE_LENGTH ? `${first.slice(0, TITLE_LENGTH).trimEnd()}…` : first;
}

/** What is saved. A reply that was in flight at save time cannot resume after a reload, so it is
 *  saved the way SEND_FAILED leaves it: the last student message marked failed, a waiting phase. */
export function toStorable(state: EpisodeUI): EpisodeUI {
  const base = { ...state, error: null };
  if (state.phase !== 'awaiting_tutor') return base;
  const lastId = state.messages.at(-1)?.id;
  return {
    ...base,
    phase: state.serverState?.awaiting_cycle_confirmation ? 'awaiting_cycle_decision' : state.serverState || state.topic ? 'awaiting_student' : 'idle',
    messages: state.messages.map((m) => (m.id === lastId && m.role === 'student' ? { ...m, failed: true } : m)),
  };
}

/** Insert or replace by id, newest first, at most `cap` chats. */
export function upsertChat(store: ChatStore, chat: StoredChat, cap: number = MAX_CHATS): ChatStore {
  const chats = [chat, ...store.chats.filter((c) => c.id !== chat.id)]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, cap);
  return { version: 1, chats };
}

/** The store after this state change; unchanged when the state has no message yet. */
export function recordState(store: ChatStore, state: EpisodeUI, now: string): ChatStore {
  const id = chatIdFor(state);
  if (!id) return store;
  const saved = toStorable(state);
  return upsertChat(store, { id, title: titleFor(state), topic: state.topic, updatedAt: now, state: saved });
}

function isChat(value: unknown): value is StoredChat {
  if (!value || typeof value !== 'object') return false;
  const c = value as Record<string, unknown>;
  const s = c.state as Record<string, unknown> | undefined;
  return typeof c.id === 'string' && typeof c.title === 'string' && typeof c.updatedAt === 'string'
    && !!s && typeof s === 'object' && Array.isArray(s.messages) && Array.isArray(s.history) && typeof s.phase === 'string';
}

/** Never throws: anything unreadable becomes an empty store, and unreadable chats are dropped. */
export function parseStore(raw: string | null): ChatStore {
  if (!raw) return emptyStore();
  try {
    const value = JSON.parse(raw) as { version?: unknown; chats?: unknown };
    if (!value || value.version !== 1 || !Array.isArray(value.chats)) return emptyStore();
    return { version: 1, chats: value.chats.filter(isChat) };
  } catch {
    return emptyStore();
  }
}

/** Storage can be blocked, full or cleared: the app then works without saved chats. */
export function loadStore(): ChatStore {
  try { return parseStore(localStorage.getItem(CHAT_STORE_KEY)); } catch { return emptyStore(); }
}

export function saveStore(store: ChatStore): void {
  try { localStorage.setItem(CHAT_STORE_KEY, JSON.stringify(store)); } catch { /* not saved; the chat still works */ }
}
