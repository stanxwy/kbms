import { useEffect, useRef, useState } from 'react'
import { Button, Card, Empty, Input, List, Popconfirm, Space, Spin, Tag, Typography, message } from 'antd'
import { DeleteOutlined, PlusOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'

import {
  chatStream,
  clearSession,
  getMessages,
  getSessions,
  type SessionItem,
  type SourceItem,
  type UnauthorizedItem,
} from '../../api/ai'
import MarkdownViewer from '../../components/MarkdownViewer'
import SourceCiteCard from '../../components/SourceCiteCard'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceItem[]
  unauthorized?: UnauthorizedItem[]
  loading?: boolean
}

const genId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const loadSessions = async () => {
    try {
      setSessions(await getSessions())
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载会话失败')
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const newChat = () => {
    setCurrentSessionId(null)
    setMessages([])
  }

  const selectSession = async (sessionId: string) => {
    setCurrentSessionId(sessionId)
    setLoadingHistory(true)
    try {
      const res = await getMessages(sessionId)
      const items: ChatMessage[] = (res.items ?? []).map((h) => ({
        id: h._id || genId(),
        role: h.role === 'assistant' || h.role === 'ai' ? 'assistant' : 'user',
        content: h.text ?? '',
      }))
      setMessages(items)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载历史失败')
      setMessages([])
    } finally {
      setLoadingHistory(false)
    }
  }

  const deleteSession = async (sessionId: string) => {
    try {
      await clearSession(sessionId)
      message.success('会话已清空')
      if (currentSessionId === sessionId) newChat()
      loadSessions()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '清空会话失败')
    }
  }

  const patchMessage = (id: string, patch: Partial<ChatMessage>) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))

  const appendDelta = (id: string, delta: string) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, content: m.content + delta } : m)))

  const send = async () => {
    const question = input.trim()
    if (!question || streaming) return

    const assistantId = genId()
    setMessages((prev) => [
      ...prev,
      { id: genId(), role: 'user', content: question },
      { id: assistantId, role: 'assistant', content: '', loading: true },
    ])
    setInput('')
    setStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await chatStream(
        question,
        currentSessionId,
        (ev) => {
          if (ev.event === 'delta') {
            appendDelta(assistantId, ev.data.delta)
          } else if (ev.event === 'sources') {
            patchMessage(assistantId, { sources: ev.data.items })
          } else if (ev.event === 'unauthorized') {
            patchMessage(assistantId, { unauthorized: ev.data.items })
          } else if (ev.event === 'result') {
            patchMessage(assistantId, { content: ev.data.answer, loading: false })
            if (ev.data.session_id) setCurrentSessionId(ev.data.session_id)
          } else if (ev.event === 'error') {
            patchMessage(assistantId, { content: ev.data.error, loading: false })
          }
        },
        controller.signal,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        patchMessage(assistantId, {
          content: (e as Error).message || '问答请求失败',
          loading: false,
        })
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
      loadSessions()
    }
  }

  const stop = () => {
    abortRef.current?.abort()
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 96px)', gap: 16 }}>
      <Card
        size="small"
        title="会话"
        style={{ width: 260, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
        extra={
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={newChat}>
            新对话
          </Button>
        }
        bodyStyle={{ flex: 1, overflow: 'auto' }}
      >
        <List
          size="small"
          dataSource={sessions}
          locale={{ emptyText: <Empty description="暂无会话" /> }}
          renderItem={(item) => (
            <List.Item
              style={{ cursor: 'pointer', padding: '8px 0' }}
              actions={[
                <Popconfirm key="del" title="确认清空该会话？" onConfirm={() => deleteSession(item.session_id)}>
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>,
              ]}
              onClick={() => selectSession(item.session_id)}
            >
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Typography.Text
                  ellipsis
                  strong={item.session_id === currentSessionId}
                  style={{ maxWidth: 180 }}
                >
                  {item.last_question ?? '（会话）'}
                </Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {item.updated_at ? item.updated_at.slice(0, 16).replace('T', ' ') : ''}
                </Typography.Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>

      <Card style={{ flex: 1, display: 'flex', flexDirection: 'column' }} bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'auto', paddingBottom: 16 }}>
          <Spin spinning={loadingHistory}>
            {messages.length === 0 ? (
              <Empty description="开始你的提问" style={{ marginTop: 120 }} />
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                    marginBottom: 16,
                  }}
                >
                  <div style={{ maxWidth: '78%' }}>
                    <Tag color={m.role === 'user' ? 'blue' : 'green'} style={{ marginBottom: 4 }}>
                      {m.role === 'user' ? '我' : 'AI'}
                    </Tag>
                    {m.role === 'assistant' ? (
                      <div className="markdown-body">
                        {m.loading && !m.content ? (
                          <Typography.Text type="secondary">正在思考…</Typography.Text>
                        ) : (
                          <MarkdownViewer content={m.content} />
                        )}
                        {m.sources || m.unauthorized ? (
                          <SourceCiteCard sources={m.sources ?? []} unauthorized={m.unauthorized ?? []} />
                        ) : null}
                      </div>
                    ) : (
                      <div style={{ background: '#e6f4ff', padding: '8px 12px', borderRadius: 8 }}>
                        {m.content}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </Spin>
        </div>
        <div ref={bottomRef} />
        <Space.Compact style={{ width: '100%', marginTop: 8 }}>
          <Input.TextArea
            value={input}
            autoSize={{ minRows: 1, maxRows: 6 }}
            placeholder="输入你的问题，Ctrl/⌘ + Enter 发送"
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={(e) => {
              if (e.ctrlKey || e.metaKey) {
                e.preventDefault()
                send()
              }
            }}
          />
          {streaming ? (
            <Button danger icon={<StopOutlined />} onClick={stop}>
              停止
            </Button>
          ) : (
            <Button type="primary" icon={<SendOutlined />} onClick={send}>
              发送
            </Button>
          )}
        </Space.Compact>
      </Card>
    </div>
  )
}