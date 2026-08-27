import { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  TreeSelect,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'

import {
  createDepartment,
  deleteDepartment,
  getDepartments,
  getUsers,
  updateDepartment,
  type DepartmentTreeNode,
} from '../../api/org'
import { usePermission } from '../../hooks/usePermission'

interface DeptFormValues {
  name: string
  parent_id?: number | null
  leader_id?: number | null
  sort_order?: number
}

type TreeOption = { title: string; value: number; children?: TreeOption[] }

function toTreeData(nodes: DepartmentTreeNode[]): TreeOption[] {
  return nodes.map((n) => ({
    title: n.name,
    value: n.id,
    children: n.children?.length ? toTreeData(n.children) : undefined,
  }))
}

export default function DepartmentsPage() {
  const { can } = usePermission()
  const editable = can('menu:org:dept')

  const [tree, setTree] = useState<DepartmentTreeNode[]>([])
  const [users, setUsers] = useState<{ id: number; label: string }[]>([])
  const [loading, setLoading] = useState(false)

  const [form] = Form.useForm<DeptFormValues>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DepartmentTreeNode | null>(null)
  const [saving, setSaving] = useState(false)

  const userMap = useMemo(() => {
    const m = new Map<number, string>()
    users.forEach((u) => m.set(u.id, u.label))
    return m
  }, [users])

  const load = async () => {
    setLoading(true)
    try {
      setTree(await getDepartments())
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载部门失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    getUsers({ page: 1, page_size: 100 })
      .then((r) =>
        setUsers(r.items.map((u) => ({ id: u.id, label: u.display_name ?? u.username }))),
      )
      .catch(() => undefined)
  }, [])

  const openCreate = (parent?: DepartmentTreeNode) => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      parent_id: parent?.id ?? null,
      sort_order: 0,
      leader_id: null,
    })
    setModalOpen(true)
  }

  const openEdit = (record: DepartmentTreeNode) => {
    setEditing(record)
    form.resetFields()
    form.setFieldsValue({
      name: record.name,
      parent_id: record.parent_id ?? null,
      leader_id: record.leader_id ?? null,
      sort_order: record.sort_order,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (editing) {
        await updateDepartment(editing.id, {
          name: values.name ?? null,
          parent_id: values.parent_id ?? null,
          leader_id: values.leader_id ?? null,
          sort_order: values.sort_order ?? null,
        })
        message.success('部门已更新')
      } else {
        await createDepartment({
          name: values.name,
          parent_id: values.parent_id ?? null,
          leader_id: values.leader_id ?? null,
          sort_order: values.sort_order ?? 0,
        })
        message.success('部门已创建')
      }
      setModalOpen(false)
      load()
    } catch (e) {
      if (e instanceof Error) message.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (record: DepartmentTreeNode) => {
    try {
      await deleteDepartment(record.id)
      message.success('部门已删除')
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const columns: ColumnsType<DepartmentTreeNode> = [
    { title: '部门名称', dataIndex: 'name', key: 'name' },
    {
      title: '负责人',
      dataIndex: 'leader_id',
      key: 'leader_id',
      render: (v: number | null) => (v != null ? userMap.get(v) ?? v : '-'),
    },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => openCreate(record)}>
            添加子部门
          </Button>
          <Button type="link" size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该部门？" onConfirm={() => handleDelete(record)}>
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
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={load}>
          刷新
        </Button>
        {editable && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openCreate()}>
            新建顶级部门
          </Button>
        )}
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={tree}
        pagination={false}
        defaultExpandAllRows
      />

      <Modal
        title={editing ? '编辑部门' : '新建部门'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="部门名称" rules={[{ required: true, message: '请输入部门名称' }]}>
            <Input placeholder="部门名称" />
          </Form.Item>
          <Form.Item name="parent_id" label="上级部门">
            <TreeSelect
              allowClear
              treeData={toTreeData(tree)}
              treeDefaultExpandAll
              placeholder="不选则为顶级部门"
            />
          </Form.Item>
          <Form.Item name="leader_id" label="负责人">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="选择负责人"
              options={users}
            />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}