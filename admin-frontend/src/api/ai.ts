import client from './client'
import { useAuthStore } from '../store/auth'

// ---- 类型定义（对齐后端 schemas/ai.py） ----

export interface SessionItem {
  session_id: string
  last_question: string | null
  updated_at: string | null
}

export interface HistoryItem {
  _id: string
  session_id: string
  role: string
  text: string
  rewritten_query: string
  item_names: string[]
  ts: unknown
}

export interface HistoryResult {
  session_id: string
  items: HistoryItem[]
}

export interface SourceItem {
  unit_id: number
  title: string
  source_file_name: string
}

export interface UnauthorizedItem {
  unit_id: number
  title: string
}

/** SSE 流式事件（后端 chat_stream 推送的事件协议）。 */
export type ChatStreamEvent =
  | { event: 'delta'; data: { delta: string } }
  | { event: 'sources'; data: { items: SourceItem[] } }
  | { event: 'unauthorized'; data: { items: UnauthorizedItem[] } }
  | {
      event: 'result'
      data: { answer: string; session_id: string; from_faq?: boolean; faq_id?: number }
    }
  | { event: 'error'; data: { error: string } }

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

/**
 * 鉴权问答（SSE 流式）。axios 拦截器会做 JSON 解包，无法用于流式，
 * 故用 fetch 手动解析 `event:/data:` 帧，逐事件回调。
 */
export async function chatStream(
  question: string,
  sessionId: string | null,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = useAuthStore.getState().token
  const response = await fetch(`${API_BASE}/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`问答请求失败（HTTP ${response.status}）`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      // 以空行分隔帧（后端 _sse_pack 每帧以 \n\n 结尾）。
      const frames = buffer.split('\n\n')
      buffer = frames.pop() ?? ''
      for (const frame of frames) {
        const parsed = parseSseFrame(frame)
        if (parsed) onEvent(parsed)
      }
    }
  } finally {
    reader.releaseLock()
  }
}

function parseSseFrame(frame: string): ChatStreamEvent | null {
  let event = ''
  let dataText = ''
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataText += line.slice(5).trim()
  }
  if (!event || !dataText) return null
  try {
    const data = JSON.parse(dataText)
    const e = event as ChatStreamEvent['event']
    return { event: e, data } as ChatStreamEvent
  } catch {
    return null
  }
}

// ---- 会话管理 ----
export const getSessions = () => client.get<SessionItem[], SessionItem[]>('/ai/sessions')

export const getMessages = (sessionId: string) =>
  client.get<HistoryResult, HistoryResult>(`/ai/sessions/${sessionId}/messages`)

export const clearSession = (sessionId: string) =>
  client.delete<{ message: string; deleted_count: number }, { message: string; deleted_count: number }>(
    `/ai/sessions/${sessionId}`,
  )