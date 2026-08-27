import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd'
import { InboxOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons'

import {
  deleteUnits,
  getImportTask,
  getUnitPermissions,
  getUnits,
  importKnowledge,
  updateUnit,
  type ImportTaskStatus,
  type KnowledgeUnitOut,
  type UnitPermissionItem,
} from '../../api/knowledge'
import PermissionDialog from '../../components/PermissionDialog'
import { usePermission } from '../../hooks/usePermission'

interface UnitFormValues {
  title: string
  summary?: string
  category?: string
  status?: string
  content?: string
}

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' },
]

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  draft: { color: 'default', text: '草稿' },
  published: { color: 'green', text: '已发布' },
  archived: { color: 'orange', text: '已归档' },
}

/** 单个导入任务的实时进度。 */
interface ImportItem {
  key: string
  fileName: string
  taskId: string
  status: 'submitting' | 'processing' | 'completed' | 'failed'
  percent: number
  runningNodes: string[]
}

/** 导入任务状态文字。 */
const IMPORT_STATUS_TEXT: Record<ImportItem['status'], string> = {
  submitting: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
}

const POLL_INTERVAL_MS = 1500

/** RAG 流水线总节点数：PDF 走解析拆分共 8 步，其余 7 步（与 app ingest 页对齐）。 */
function totalNodesOf(fileName: string): number {
  return fileName.toLowerCase().endsWith('.pdf') ? 8 : 7
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function KnowledgePage() {
  const { can } = usePermission()
  const canImport = can('op:knowledge:import')
  const canUpdate = can('op:knowledge:unit:update')
  const canDelete = can('op:knowledge:unit:delete')

  const [list, setList] = useState<KnowledgeUnitOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState<string | undefined>()
  const [status, setStatus] = useState<string | undefined>()
  const [fileType, setFileType] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [importing, setImporting] = useState(false)
  const [importItems, setImportItems] = useState<ImportItem[]>([])
  const pollTimer = useRef<number | null>(null)

  const [form] = Form.useForm<UnitFormValues>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<KnowledgeUnitOut | null>(null)
  const [saving, setSaving] = useState(false)

  const [permUnit, setPermUnit] = useState<KnowledgeUnitOut | null>(null)
  const [permInitial, setPermInitial] = useState<UnitPermissionItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getUnits({
        keyword: keyword || undefined,
        category,
        status,
        file_type: fileType,
        page,
        page_size: pageSize,
      })
      setList(res.items)
      setTotal(res.total)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载知识单元失败')
    } finally {
      setLoading(false)
    }
  }, [keyword, category, status, fileType, page, pageSize])

  useEffect(() => {
    load()
  }, [load])

  const handleImport = async () => {
    const files = fileList
      .map((f) => f.originFileObj)
      .filter((f): f is NonNullable<typeof f> => f !== undefined)
    if (files.length === 0) {
      message.warning('请先选择文件')
      return
    }
    setImporting(true)
    try {
      const res = await importKnowledge(files)
      const items: ImportItem[] = files.map((f, i) => ({
        key: `${Date.now()}-${i}`,
        fileName: f.name,
        taskId: res.task_ids[i],
        status: 'submitting',
        percent: 0,
        runningNodes: [],
      }))
      setImportItems(items)
      setFileList([])
      schedulePoll(items)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '导入失败')
    } finally {
      setImporting(false)
    }
  }

  /** 将一次任务状态查询合并为导入项（进度算法与 app ingest 页一致：完成节点/总节点）。 */
  const mergeTaskStatus = (item: ImportItem, status: ImportTaskStatus): ImportItem => {
    if (item.status === 'completed' || item.status === 'failed') return item
    if (status.status === 'completed') {
      return { ...item, status: 'completed', percent: 100, runningNodes: [] }
    }
    if (status.status === 'failed') {
      return { ...item, status: 'failed', runningNodes: [] }
    }
    const total = totalNodesOf(item.fileName)
    const done = status.done_list?.length ?? 0
    let percent = (done / total) * 100
    if ((status.running_list?.length ?? 0) > 0) percent += (0.5 / total) * 100
    return { ...item, status: 'processing', percent, runningNodes: status.running_list ?? [] }
  }

  /** 递归轮询各任务直至全部结束；组件卸载时清理计时器。 */
  const schedulePoll = (items: ImportItem[]) => {
    if (pollTimer.current) window.clearTimeout(pollTimer.current)
    pollTimer.current = window.setTimeout(async () => {
      const updated = await Promise.all(
        items.map(async (it) => {
          if (it.status === 'completed' || it.status === 'failed') return it
          try {
            return mergeTaskStatus(it, await getImportTask(it.taskId))
          } catch {
            return it
          }
        }),
      )
      setImportItems(updated)
      if (updated.some((it) => it.status === 'submitting' || it.status === 'processing')) {
        schedulePoll(updated)
      } else {
        // 全部结束：刷新一次知识单元列表，展示新入库内容。
        load()
      }
    }, POLL_INTERVAL_MS)
  }

  const clearImportItems = () => {
    if (pollTimer.current) window.clearTimeout(pollTimer.current)
    pollTimer.current = null
    setImportItems([])
  }

  useEffect(() => {
    return () => {
      if (pollTimer.current) window.clearTimeout(pollTimer.current)
    }
  }, [])

  const openEdit = (record: KnowledgeUnitOut) => {
    setEditing(record)
    form.resetFields()
    form.setFieldsValue({
      title: record.title,
      summary: record.summary ?? undefined,
      category: record.category ?? undefined,
      status: record.status,
      content: record.content ?? undefined,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    if (!editing) return
    setSaving(true)
    try {
      await updateUnit(editing.id, {
        title: values.title ?? null,
        summary: values.summary ?? null,
        category: values.category ?? null,
        status: values.status ?? null,
        content: values.content ?? null,
      })
      message.success('知识单元已更新')
      setModalOpen(false)
      load()
    } catch (e) {
      if (e instanceof Error) message.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const openPermission = async (record: KnowledgeUnitOut) => {
    setPermUnit(record)
    setPermInitial([])
    try {
      setPermInitial(await getUnitPermissions(record.id))
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载权限失败')
    }
  }

  const handleDelete = async (ids: number[]) => {
    try {
      await deleteUnits(ids)
      message.success('已删除所选知识单元')
      setSelectedIds([])
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const columns: ColumnsType<KnowledgeUnitOut> = [
    { title: '单元编码', dataIndex: 'unit_code', key: 'unit_code', width: 160 },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '分类', dataIndex: 'category', key: 'category', render: (v: string | null) => v ?? '-' },
    {
      title: '来源文件',
      dataIndex: 'source_file_name',
      key: 'source_file_name',
      ellipsis: true,
    },
    { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 90 },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (v: number) => formatSize(v),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => {
        const t = STATUS_TAG[v] ?? { color: 'default', text: v }
        return <Tag color={t.color}>{t.text}</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          {canUpdate && (
            <Button type="link" size="small" onClick={() => openEdit(record)}>
              编辑
            </Button>
          )}
          {canUpdate && (
            <Button type="link" size="small" onClick={() => openPermission(record)}>
              权限
            </Button>
          )}
          {canDelete && (
            <Popconfirm title="确认删除该知识单元？" onConfirm={() => handleDelete([record.id])}>
              <Button type="link" size="small" danger>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          allowClear
          placeholder="标题 / 来源文件"
          style={{ width: 220 }}
          onSearch={(v) => {
            setPage(1)
            setKeyword(v)
          }}
        />
        <Input
          allowClear
          placeholder="分类"
          style={{ width: 140 }}
          value={category}
          onChange={(e) => setCategory(e.target.value || undefined)}
        />
        <Button
          onClick={() => {
            setPage(1)
            load()
          }}
        >
          筛选
        </Button>
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 120 }}
          value={status}
          onChange={(v) => {
            setPage(1)
            setStatus(v)
          }}
          options={STATUS_OPTIONS}
        />
        <Select
          allowClear
          placeholder="文件类型"
          style={{ width: 120 }}
          value={fileType}
          onChange={(v) => {
            setPage(1)
            setFileType(v)
          }}
          options={[
            { label: 'pdf', value: 'pdf' },
            { label: 'docx', value: 'docx' },
            { label: 'md', value: 'md' },
            { label: 'txt', value: 'txt' },
            { label: 'manual', value: 'manual' },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={load}>
          刷新
        </Button>
      </Space>

      {canImport && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <Upload
              multiple
              fileList={fileList}
              beforeUpload={() => false}
              showUploadList={false}
              onChange={({ fileList: fl }) => setFileList(fl)}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
            <Button type="primary" icon={<InboxOutlined />} loading={importing} onClick={handleImport}>
              开始导入
            </Button>
            {canDelete && selectedIds.length > 0 && (
              <Popconfirm
                title={`确认删除选中的 ${selectedIds.length} 个知识单元？`}
                onConfirm={() => handleDelete(selectedIds)}
              >
                <Button danger>批量删除</Button>
              </Popconfirm>
            )}
          </div>
          {fileList.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12, marginRight: 4 }}>
                已选择：
              </Typography.Text>
              {fileList.map((f, i) => (
                <Tag key={f.uid ?? i} closable onClose={() => setFileList((fl) => fl.filter((x) => x !== f))}>
                  {f.name}
                </Tag>
              ))}
            </div>
          )}
        </div>
      )}

      {importItems.length > 0 && (
        <Card size="small" title="导入进度" style={{ marginBottom: 16 }} extra={<Button type="link" onClick={clearImportItems}>清空</Button>}>
          <List
            size="small"
            dataSource={importItems}
            renderItem={(it) => {
              const active = it.status === 'submitting' || it.status === 'processing'
              const progressStatus =
                it.status === 'failed' ? 'exception' : it.status === 'completed' ? 'success' : 'active'
              return (
                <List.Item>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Space size={8}>
                        <Typography.Text ellipsis={{ tooltip: it.fileName }} style={{ maxWidth: 320 }}>
                          {it.fileName}
                        </Typography.Text>
                        <Tag color={it.status === 'failed' ? 'red' : active ? 'processing' : it.status === 'completed' ? 'green' : 'default'}>
                          {IMPORT_STATUS_TEXT[it.status]}
                        </Tag>
                        {it.runningNodes.length > 0 && (
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            正在 {it.runningNodes.join('、')}
                          </Typography.Text>
                        )}
                      </Space>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {it.percent.toFixed(0)}%
                      </Typography.Text>
                    </div>
                    <Progress percent={Number(it.percent.toFixed(0))} status={progressStatus} size="small" />
                  </div>
                </List.Item>
              )
            }}
          />
        </Card>
      )}

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={list}
        rowSelection={
          canDelete ? { selectedRowKeys: selectedIds, onChange: (keys) => setSelectedIds(keys as number[]) } : undefined
        }
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />

      <Modal
        title="编辑知识单元"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        width={720}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="知识单元标题" />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Input placeholder="所属分类（可选）" />
          </Form.Item>
          <Form.Item name="summary" label="摘要">
            <Input.TextArea rows={2} placeholder="内容摘要（可选）" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="content" label="正文">
            <Input.TextArea rows={8} placeholder="知识单元正文内容" />
          </Form.Item>
        </Form>
      </Modal>

      <PermissionDialog
        open={!!permUnit}
        unitId={permUnit?.id ?? 0}
        initial={permInitial}
        onClose={() => setPermUnit(null)}
        onSaved={load}
      />
    </div>
  )
}