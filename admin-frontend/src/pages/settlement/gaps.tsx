import { useCallback, useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { ReloadOutlined } from '@ant-design/icons'

import {
  getKnowledgeGaps,
  ignoreGap,
  resolveGap,
  type KnowledgeGapItem,
} from '../../api/settlement'

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  unresolved: { color: 'volcano', text: '未解决' },
  resolved: { color: 'green', text: '已补全' },
  ignored: { color: 'default', text: '已忽略' },
}

export default function GapsPage() {
  const [list, setList] = useState<KnowledgeGapItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  const [resolveTarget, setResolveTarget] = useState<KnowledgeGapItem | null>(null)
  const [form] = Form.useForm<{ title?: string; content?: string; category?: string }>()
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getKnowledgeGaps({
        status,
        keyword: keyword || undefined,
        page,
        page_size: 20,
      })
      setList(res.items)
      setTotal(res.total)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载知识缺口失败')
    } finally {
      setLoading(false)
    }
  }, [status, keyword, page])

  useEffect(() => {
    load()
  }, [load])

  const openResolve = (record: KnowledgeGapItem) => {
    setResolveTarget(record)
    form.resetFields()
    form.setFieldsValue({ title: record.question_pattern, content: undefined, category: undefined })
  }

  const doResolve = async () => {
    if (!resolveTarget) return
    const values = await form.validateFields()
    setSaving(true)
    try {
      await resolveGap(resolveTarget.id, {
        title: values.title,
        content: values.content,
        category: values.category,
      })
      message.success('已创建知识单元补全缺口')
      setResolveTarget(null)
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '补全失败')
    } finally {
      setSaving(false)
    }
  }

  const doIgnore = async (record: KnowledgeGapItem) => {
    try {
      await ignoreGap(record.id)
      message.success('已忽略该缺口')
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '忽略失败')
    }
  }

  const columns: ColumnsType<KnowledgeGapItem> = [
    { title: '问题模式', dataIndex: 'question_pattern', key: 'question_pattern', ellipsis: true },
    {
      title: '样本问题',
      dataIndex: 'sample_questions',
      key: 'sample_questions',
      render: (v: string[]) =>
        v.length ? v.slice(0, 3).map((q) => <Tag key={q}>{q}</Tag>) : '-',
    },
    { title: '提问次数', dataIndex: 'ask_count', key: 'ask_count', width: 90 },
    {
      title: '最近提问',
      dataIndex: 'last_asked_at',
      key: 'last_asked_at',
      width: 160,
      render: (v: string | null) => (v ? String(v).slice(0, 16).replace('T', ' ') : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => {
        const t = STATUS_TAG[v] ?? { color: 'default', text: v }
        return <Tag color={t.color}>{t.text}</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          {record.status === 'unresolved' && (
            <>
              <Button type="link" size="small" onClick={() => openResolve(record)}>
                补全
              </Button>
              <Popconfirm title="确认忽略该缺口？" onConfirm={() => doIgnore(record)}>
                <Button type="link" size="small">
                  忽略
                </Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          allowClear
          placeholder="搜索问题模式"
          style={{ width: 220 }}
          onSearch={(v) => {
            setPage(1)
            setKeyword(v)
          }}
        />
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 140 }}
          value={status}
          onChange={(v) => {
            setPage(1)
            setStatus(v)
          }}
          options={[
            { label: '未解决', value: 'unresolved' },
            { label: '已补全', value: 'resolved' },
            { label: '已忽略', value: 'ignored' },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={load}>
          刷新
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={list}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          onChange: (p) => setPage(p),
        }}
      />

      <Modal
        title={`补全缺口：${resolveTarget?.question_pattern ?? ''}`}
        open={!!resolveTarget}
        onCancel={() => setResolveTarget(null)}
        onOk={doResolve}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="知识单元标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Input placeholder="可选分类" />
          </Form.Item>
          <Form.Item name="content" label="内容">
            <Input.TextArea rows={8} placeholder="知识单元正文内容" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}