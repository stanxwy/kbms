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
  Tag,
  TreeSelect,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'

import {
  createUser,
  getDepartments,
  getRoles,
  getUsers,
  resetPassword,
  updateUser,
  updateUserStatus,
  type DepartmentTreeNode,
  type RoleOut,
  type UserOut,
} from '../../api/org'
import { usePermission } from '../../hooks/usePermission'

interface UserFormValues {
  username?: string
  password?: string
  display_name?: string
  department_id?: number | null
  role_ids?: number[]
  status?: number
}

type TreeOption = { title: string; value: number; children?: TreeOption[] }

function toTreeData(nodes: DepartmentTreeNode[]): TreeOption[] {
  return nodes.map((n) => ({
    title: n.name,
    value: n.id,
    children: n.children?.length ? toTreeData(n.children) : undefined,
  }))
}

export default function UsersPage() {
  const { can } = usePermission()
  const editable = can('menu:org:user')

  const [list, setList] = useState<UserOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [departmentId, setDepartmentId] = useState<number | undefined>()
  const [status, setStatus] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)

  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([])
  const [roles, setRoles] = useState<RoleOut[]>([])

  const [form] = Form.useForm<UserFormValues>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<UserOut | null>(null)
  const [saving, setSaving] = useState(false)

  const [resetUser, setResetUser] = useState<UserOut | null>(null)
  const [resetForm] = Form.useForm<{ password: string }>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getUsers({
        keyword: keyword || undefined,
        department_id: departmentId,
        status,
        page,
        page_size: pageSize,
      })
      setList(res.items)
      setTotal(res.total)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载用户失败')
    } finally {
      setLoading(false)
    }
  }, [keyword, departmentId, status, page, pageSize])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!modalOpen) return
    Promise.all([getDepartments(), getRoles()])
      .then(([d, r]) => {
        setDepartments(d)
        setRoles(r)
      })
      .catch((e) => message.error(e instanceof Error ? e.message : '加载选项失败'))
  }, [modalOpen])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 1, role_ids: [] })
    setModalOpen(true)
  }

  const openEdit = (record: UserOut) => {
    setEditing(record)
    form.resetFields()
    form.setFieldsValue({
      display_name: record.display_name ?? undefined,
      department_id: record.department_id ?? undefined,
      role_ids: record.roles.map((r) => r.id),
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (editing) {
        await updateUser(editing.id, {
          display_name: values.display_name ?? null,
          department_id: values.department_id ?? null,
          role_ids: values.role_ids ?? [],
        })
        message.success('用户已更新')
      } else {
        await createUser({
          username: values.username!,
          password: values.password!,
          display_name: values.display_name ?? null,
          department_id: values.department_id ?? null,
          role_ids: values.role_ids ?? [],
          status: values.status ?? 1,
        })
        message.success('用户已创建')
      }
      setModalOpen(false)
      load()
    } catch (e) {
      if (e instanceof Error) message.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleResetPassword = async () => {
    const { password } = await resetForm.validateFields()
    if (!resetUser) return
    try {
      await resetPassword(resetUser.id, password)
      message.success('密码已重置')
      setResetUser(null)
      resetForm.resetFields()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '重置失败')
    }
  }

  const toggleStatus = async (record: UserOut) => {
    try {
      await updateUserStatus(record.id, record.status === 1 ? 0 : 1)
      message.success('状态已更新')
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '操作失败')
    }
  }

  const columns: ColumnsType<UserOut> = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    {
      title: '姓名',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (v: string | null) => v ?? '-',
    },
    {
      title: '部门',
      dataIndex: 'department_name',
      key: 'department_name',
      render: (v: string | null) => v ?? '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: number) => (v === 1 ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag>),
    },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: UserOut['roles']) =>
        roles.length ? roles.map((r) => <Tag key={r.id}>{r.role_name}</Tag>) : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button type="link" size="small" onClick={() => setResetUser(record)}>
            重置密码
          </Button>
          <Popconfirm
            title={record.status === 1 ? '确认停用该用户？' : '确认启用该用户？'}
            onConfirm={() => toggleStatus(record)}
          >
            <Button type="link" size="small" danger={record.status === 1}>
              {record.status === 1 ? '停用' : '启用'}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          allowClear
          placeholder="用户名 / 姓名"
          style={{ width: 200 }}
          onSearch={(v) => {
            setPage(1)
            setKeyword(v)
          }}
        />
        <TreeSelect
          allowClear
          placeholder="全部部门"
          style={{ width: 200 }}
          treeData={toTreeData(departments)}
          treeDefaultExpandAll
          value={departmentId}
          onChange={(v) => {
            setPage(1)
            setDepartmentId(v as number | undefined)
          }}
        />
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 120 }}
          value={status}
          onChange={(v) => {
            setPage(1)
            setStatus(v)
          }}
          options={[
            { label: '启用', value: 1 },
            { label: '停用', value: 0 },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={load}>
          刷新
        </Button>
        {editable && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建用户
          </Button>
        )}
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={list}
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
        title={editing ? '编辑用户' : '新建用户'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <>
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="登录账号" />
              </Form.Item>
              <Form.Item
                name="password"
                label="初始密码"
                rules={[{ required: true, min: 6, message: '密码至少 6 位' }]}
              >
                <Input.Password placeholder="登录密码" />
              </Form.Item>
            </>
          )}
          <Form.Item name="display_name" label="姓名">
            <Input placeholder="显示姓名" />
          </Form.Item>
          <Form.Item name="department_id" label="所属部门">
            <TreeSelect
              allowClear
              treeData={toTreeData(departments)}
              treeDefaultExpandAll
              placeholder="选择部门"
            />
          </Form.Item>
          <Form.Item name="role_ids" label="角色">
            <Select
              mode="multiple"
              placeholder="分配角色"
              options={roles.map((r) => ({ label: r.role_name, value: r.id }))}
            />
          </Form.Item>
          {!editing && (
            <Form.Item name="status" label="状态">
              <Select
                options={[
                  { label: '启用', value: 1 },
                  { label: '停用', value: 0 },
                ]}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title={`重置密码：${resetUser?.username ?? ''}`}
        open={!!resetUser}
        onCancel={() => setResetUser(null)}
        onOk={handleResetPassword}
        destroyOnClose
      >
        <Form form={resetForm} layout="vertical">
          <Form.Item
            name="password"
            label="新密码"
            rules={[{ required: true, min: 6, message: '密码至少 6 位' }]}
          >
            <Input.Password placeholder="新密码" autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}