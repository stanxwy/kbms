import { useEffect, useState } from 'react'
import { Checkbox, Form, Modal, Select, Space, message } from 'antd'

import {
  getDepartments,
  getRoles,
  getUsers,
  type DepartmentTreeNode,
  type RoleOut,
  type UserOut,
} from '../api/org'
import { setUnitPermissions, type UnitPermissionItem } from '../api/knowledge'

interface PermissionDialogProps {
  open: boolean
  unitId: number
  initial: UnitPermissionItem[]
  onClose: () => void
  onSaved: () => void
}

interface Option {
  value: number
  label: string
}

function flattenDepartments(nodes: DepartmentTreeNode[], depth = 0): Option[] {
  const options: Option[] = []
  for (const n of nodes) {
    options.push({ value: n.id, label: `${'　'.repeat(depth)}${n.name}` })
    if (n.children?.length) options.push(...flattenDepartments(n.children, depth + 1))
  }
  return options
}

/** 知识单元数据权限四维配置弹窗（global/department/role/user，全量覆盖）。 */
export default function PermissionDialog({
  open,
  unitId,
  initial,
  onClose,
  onSaved,
}: PermissionDialogProps) {
  const [global, setGlobal] = useState(false)
  const [deptIds, setDeptIds] = useState<number[]>([])
  const [roleIds, setRoleIds] = useState<number[]>([])
  const [userIds, setUserIds] = useState<number[]>([])

  const [departments, setDepartments] = useState<Option[]>([])
  const [roles, setRoles] = useState<RoleOut[]>([])
  const [users, setUsers] = useState<UserOut[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setGlobal(initial.some((p) => p.target_type === 'global'))
    setDeptIds(initial.filter((p) => p.target_type === 'department').map((p) => p.target_id))
    setRoleIds(initial.filter((p) => p.target_type === 'role').map((p) => p.target_id))
    setUserIds(initial.filter((p) => p.target_type === 'user').map((p) => p.target_id))

    // 加载选择器数据（部门树 / 角色列表 / 前 100 用户）。
    setLoading(true)
    Promise.all([
      getDepartments().then(flattenDepartments),
      getRoles(),
      getUsers({ page: 1, page_size: 100 }).then((r) => r.items),
    ])
      .then(([depts, rolesData, usersData]) => {
        setDepartments(depts)
        setRoles(rolesData)
        setUsers(usersData)
      })
      .catch((e) => message.error(e instanceof Error ? e.message : '加载选择项失败'))
      .finally(() => setLoading(false))
  }, [open, initial])

  const handleSave = async () => {
    const permissions: UnitPermissionItem[] = []
    if (global) permissions.push({ target_type: 'global', target_id: 0 })
    deptIds.forEach((id) => permissions.push({ target_type: 'department', target_id: id }))
    roleIds.forEach((id) => permissions.push({ target_type: 'role', target_id: id }))
    userIds.forEach((id) => permissions.push({ target_type: 'user', target_id: id }))

    setSaving(true)
    try {
      await setUnitPermissions(unitId, permissions)
      message.success('数据权限已保存')
      onSaved()
      onClose()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="配置数据权限"
      open={open}
      onCancel={onClose}
      onOk={handleSave}
      confirmLoading={saving}
      okText="保存"
      cancelText="取消"
      destroyOnClose
    >
      <Form layout="vertical">
        <Form.Item label="公开访问">
          <Checkbox checked={global} onChange={(e) => setGlobal(e.target.checked)}>
            全局可见（所有登录用户可访问）
          </Checkbox>
        </Form.Item>
        <Form.Item label="授权部门">
          <Select
            mode="multiple"
            loading={loading}
            placeholder="按部门授权（含其下级部门）"
            options={departments}
            value={deptIds}
            onChange={setDeptIds}
            optionFilterProp="label"
            allowClear
          />
        </Form.Item>
        <Form.Item label="授权角色">
          <Select
            mode="multiple"
            loading={loading}
            placeholder="按角色授权"
            value={roleIds}
            onChange={setRoleIds}
            options={roles.map((r) => ({ value: r.id, label: r.role_name }))}
            optionFilterProp="label"
            allowClear
          />
        </Form.Item>
        <Form.Item label="授权用户">
          <Select
            mode="multiple"
            loading={loading}
            placeholder="按用户授权"
            value={userIds}
            onChange={setUserIds}
            options={users.map((u) => ({ value: u.id, label: u.display_name ?? u.username }))}
            optionFilterProp="label"
            allowClear
          />
        </Form.Item>
      </Form>
      <Space direction="vertical" size={0}>
        <span style={{ color: '#999', fontSize: 12 }}>
          满足上述任一授权（公开 / 部门 / 角色 / 用户）即可访问该知识单元。
        </span>
      </Space>
    </Modal>
  )
}