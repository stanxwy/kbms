import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { ReloadOutlined } from '@ant-design/icons'

import {
  deleteFaq,
  getFaqRecommendations,
  getFaqs,
  reviewFaq,
  updateFaq,
  type FAQItem,
} from '../../api/settlement'
import { usePermission } from '../../hooks/usePermission'

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  pending_review: { color: 'processing', text: '待审核' },
  published: { color: 'green', text: '已发布' },
  rejected: { color: 'red', text: '已驳回' },
}

export default function FaqsPage() {
  const { can } = usePermission()
  const canReview = can('op:settlement:faq:review')

  // 待审核
  const [pending, setPending] = useState<FAQItem[]>([])
  const [pendingTotal, setPendingTotal] = useState(0)
  const [pendingPage, setPendingPage] = useState(1)
  const [pendingLoading, setPendingLoading] = useState(false)

  // 全部
  const [list, setList] = useState<FAQItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  const [reviewTarget, setReviewTarget] = useState<FAQItem | null>(null)
  const [reviewForm] = Form.useForm<{ edited_answer?: string; category?: string }>()
  const [reviewing, setReviewing] = useState(false)

  const [editTarget, setEditTarget] = useState<FAQItem | null>(null)
  const [editForm] = Form.useForm<{ question: string; answer: string; category?: string }>()
  const [saving, setSaving] = useState(false)

  const pageSize = 20

  const loadPending = useCallback(async () => {
    setPendingLoading(true)
    try {
      const res = await getFaqRecommendations(pendingPage, pageSize)
      setPending(res.items)
      setPendingTotal(res.total)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载待审核 FAQ 失败')
    } finally {
      setPendingLoading(false)
    }
  }, [pendingPage])

  const loadList = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getFaqs({ status, keyword: keyword || undefined, page, page_size: pageSize })
      setList(res.items)
      setTotal(res.total)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载 FAQ 失败')
    } finally {
      setLoading(false)
    }
  }, [status, keyword, page])

  useEffect(() => {
    loadPending()
  }, [loadPending])

  useEffect(() => {
    loadList()
  }, [loadList])

  const doApprove = async () => {
    if (!reviewTarget) return
    const values = await reviewForm.validateFields()
    setReviewing(true)
    try {
      await reviewFaq(reviewTarget.id, {
        action: 'approve',
        edited_answer: values.edited_answer || undefined,
        category: values.category || undefined,
      })
      message.success('FAQ 已发布')
      setReviewTarget(null)
      loadPending()
      loadList()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '审核失败')
    } finally {
      setReviewing(false)
    }
  }

  const doReject = async (record: FAQItem) => {
    try {
      await reviewFaq(record.id, { action: 'reject' })
      message.success('FAQ 已驳回')
      loadPending()
      loadList()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '驳回失败')
    }
  }

  const openEdit = (record: FAQItem) => {
    setEditTarget(record)
    editForm.resetFields()
    editForm.setFieldsValue({
      question: record.question,
      answer: record.answer,
      category: record.category ?? undefined,
    })
  }

  const doSaveEdit = async () => {
    if (!editTarget) return
    const values = await editForm.validateFields()
    setSaving(true)
    try {
      await updateFaq(editTarget.id, {
        question: values.question,
        answer: values.answer,
        category: values.category ?? null,
      })
      message.success('FAQ 已更新')
      setEditTarget(null)
      loadList()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '更新失败')
    } finally {
      setSaving(false)
    }
  }

  const doDelete = async (record: FAQItem) => {
    try {
      await deleteFaq(record.id)
      message.success('FAQ 已删除')
      loadList()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const pendingColumns: ColumnsType<FAQItem> = [
    { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true },
    { title: '命中次数', dataIndex: 'hit_count', key: 'hit_count', width: 90 },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => setReviewTarget(record)}>
            通过
          </Button>
          <Popconfirm title="确认驳回该 FAQ？" onConfirm={() => doReject(record)}>
            <Button type="link" size="small" danger>
              驳回
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const listColumns: ColumnsType<FAQItem> = [
    { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true },
    { title: '答案', dataIndex: 'answer', key: 'answer', ellipsis: true, render: (v) => v || '-' },
    { title: '分类', dataIndex: 'category', key: 'category', render: (v) => v ?? '-' },
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
    { title: '命中', dataIndex: 'hit_count', key: 'hit_count', width: 80 },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该 FAQ？" onConfirm={() => doDelete(record)}>
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Tabs
        items={[
          {
            key: 'review',
            label: `待审核${pendingTotal > 0 ? `（${pendingTotal}）` : ''}`,
            children: (
              <Table
                rowKey="id"
                loading={pendingLoading}
                columns={canReview ? pendingColumns : pendingColumns.filter((c) => c.key !== 'action')}
                dataSource={pending}
                pagination={{
                  current: pendingPage,
                  pageSize,
                  total: pendingTotal,
                  onChange: (p) => setPendingPage(p),
                }}
              />
            ),
          },
          {
            key: 'all',
            label: '全部 FAQ',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Input.Search
                    allowClear
                    placeholder="搜索问题"
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
                      { label: '待审核', value: 'pending_review' },
                      { label: '已发布', value: 'published' },
                      { label: '已驳回', value: 'rejected' },
                    ]}
                  />
                  <Button icon={<ReloadOutlined />} onClick={loadList}>
                    刷新
                  </Button>
                </Space>
                <Table
                  rowKey="id"
                  loading={loading}
                  columns={listColumns}
                  dataSource={list}
                  pagination={{
                    current: page,
                    pageSize,
                    total,
                    onChange: (p) => setPage(p),
                  }}
                />
              </>
            ),
          },
        ]}
      />

      <Modal
        title={`通过 FAQ：${reviewTarget?.question ?? ''}`}
        open={!!reviewTarget}
        onCancel={() => setReviewTarget(null)}
        onOk={doApprove}
        confirmLoading={reviewing}
        destroyOnClose
      >
        <Form form={reviewForm} layout="vertical">
          <Form.Item name="edited_answer" label="标准答案">
            <Input.TextArea rows={6} placeholder="填写发布后的标准答案" />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Input placeholder="可选分类" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑 FAQ"
        open={!!editTarget}
        onCancel={() => setEditTarget(null)}
        onOk={doSaveEdit}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="question" label="问题" rules={[{ required: true, message: '请输入问题' }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="answer" label="答案" rules={[{ required: true, message: '请输入答案' }]}>
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Input placeholder="可选分类" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}