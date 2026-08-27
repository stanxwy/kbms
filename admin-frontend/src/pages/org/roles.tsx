import { useEffect, useState } from 'react'
import {
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'

import {
  createRole,
  deleteRole,
  getRolePermissions,
  getRoles,
  setRolePermissions,
  updateRole,
  type PermissionItem,
  type RoleOut,
} from '../../api/org'
import { usePermission } from '../../hooks/usePermission'

interface RoleFormValues {
  role_name?: string
  role_code?: string
  description?: string
}

interface PermissionCatalogItem {
  code: string
  type: 'menu' | 'button'
  label: string
}

const PERMISSION_CATALOG: PermissionCatalogItem[] = [
  { code: 'menu:dashboard', type: 'menu', label: '数据看板' },
  { code: 'menu:org:user', type: 'menu', label: '用户管理' },
  { code: 'menu:org:dept', type: 'menu', label: '部门管理' },
  { code: 'menu:org:role', type: 'menu', label: '角色管理' },
  { code: 'menu:settlement:faq', type: 'menu', label: 'FAQ 管理' },
  { code: 'menu:settlement:gap', type: 'menu', label: '知识缺口' },
  { code: 'op:knowledge:import', type: 'button', label: '知识导入' },
  { code: 'op:knowledge:unit:read', type: 'button', label: '知识单元查看' },
  { code: 'op:knowledge:unit:update', type: 'button', label: '知识单元编辑' },
  { code: 'op:knowledge:unit:delete', type: 'button', label: '知识单元删除' },
  { code: 'op:ai:chat', type: 'button', label: 'AI 对话' },
  { code: 'op:settlement:faq:review', type: 'button', label: 'FAQ 审核' },
]

const MENU_CODES = PERMISSION_CATALOG.filter((p) => p.type === 'menu').map((p) => p.code)
const BUTTON_CODES = PERMISSION_CATALOG.filter((p) => p.type === 'button').map((p) => p.code)

export default function RolesPage() {
  const { can } = usePermission()
  const editable = can('menu:org:role')

  const [list, setList] = useState<RoleOut[]>([])
  const [loading, setLoading] = useState(false)

  const [form] = Form.useForm<RoleFormValues>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<RoleOut | null>(null)
  const [saving, setSaving] = useState(false)

  const [permRole, setPermRole] = useState<RoleOut | null>(null)
  const [permCodes, setPermCodes] = useState<string[]>([])

  const load = async () => {
    setLoading(true)
    try {
      setList(await getRoles())
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载角色失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (record: RoleOut) => {
    setEditing(record)
    form.resetFields()
    form.setFieldsValue({
      role_name: record.role_name,
      description: record.description ?? undefined,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (editing) {
        await updateRole(editing.id, {
          role_name: values.role_name ?? null,
          description: values.description ?? null,
        })
        message.success('角色已更新')
      } else {
        await createRole({
          role_name: values.role_name!,
          role_code: values.role_code!,
          description: values.description ?? null,
        })
        message.success('角色已创建')
      }
      setModalOpen(false)
      load()
    } catch (e) {
      if (e instanceof Error) message.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (record: RoleOut) => {
    try {
      await deleteRole(record.id)
      message.success('角色已删除')
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const openPermissions = async (record: RoleOut) => {
    setPermRole(record)
    try {
      const perms = await getRolePermissions(record.id)
      setPermCodes(perms.map((p) => p.permission_code))
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载权限失败')
    }
  }

  const savePermissions = async () => {
    if (!permRole) return
    const permissions: PermissionItem[] = permCodes.map((code) => {
      const item = PERMISSION_CATALOG.find((p) => p.code === code)
      return { permission_code: code, permission_type: item?.type ?? 'button' }
    })
    try {
      await setRolePermissions(permRole.id, permissions)
      message.success('权限已保存')
      setPermRole(null)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const columns: ColumnsType<RoleOut> = [
    { title: '角色名', dataIndex: 'role_name', key: 'role_name' },
    {
      title: '角色编码',
      dataIndex: 'role_code',
      key: 'role_code',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (v: string | null) => v ?? '-',
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
          <Button type="link" size="small" onClick={() => openPermissions(record)}>
            配置权限
          </Button>
          <Popconfirm title="确认删除该角色？" onConfirm={() => handleDelete(record)}>
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
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建角色
          </Button>
        )}
      </Space>

      <Table rowKey="id" loading={loading} columns={columns} dataSource={list} pagination={false} />

      <Modal
        title={editing ? '编辑角色' : '新建角色'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="role_name"
            label="角色名"
            rules={[{ required: true, message: '请输入角色名' }]}
          >
            <Input placeholder="角色显示名称" />
          </Form.Item>
          {!editing && (
            <Form.Item
              name="role_code"
              label="角色编码"
              rules={[{ required: true, message: '请输入角色编码' }]}
            >
              <Input placeholder="唯一编码，如 km_admin" />
            </Form.Item>
          )}
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="角色职责说明" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`配置权限：${permRole?.role_name ?? ''}`}
        open={!!permRole}
        onCancel={() => setPermRole(null)}
        onOk={savePermissions}
        width={640}
        destroyOnClose
      >
        <div style={{ marginBottom: 8 }}>
          <Checkbox
            checked={permCodes.length === PERMISSION_CATALOG.length}
            indeterminate={permCodes.length > 0 && permCodes.length < PERMISSION_CATALOG.length}
            onChange={(e) =>
              setPermCodes(e.target.checked ? PERMISSION_CATALOG.map((p) => p.code) : [])
            }
          >
            全选
          </Checkbox>
        </div>
        <Checkbox.Group
          value={permCodes}
          onChange={(v) => setPermCodes(v as string[])}
          style={{ width: '100%' }}
        >
          <div style={{ marginBottom: 8 }}>
            <Tag color="blue">菜单权限</Tag>
          </div>
          <Space direction="vertical" style={{ marginBottom: 16 }}>
            {MENU_CODES.map((code) => {
              const item = PERMISSION_CATALOG.find((p) => p.code === code)!
              return (
                <Checkbox key={code} value={code}>
                  {item.label}（{code}）
                </Checkbox>
              )
            })}
          </Space>
          <div style={{ marginBottom: 8 }}>
            <Tag color="green">操作权限</Tag>
          </div>
          <Space direction="vertical">
            {BUTTON_CODES.map((code) => {
              const item = PERMISSION_CATALOG.find((p) => p.code === code)!
              return (
                <Checkbox key={code} value={code}>
                  {item.label}（{code}）
                </Checkbox>
              )
            })}
          </Space>
        </Checkbox.Group>
      </Modal>
    </div>
  )
}