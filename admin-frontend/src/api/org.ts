import client from './client'
import type { PageResult } from './types'

// ---- 类型定义（对齐后端 schemas/org.py） ----

export interface DepartmentTreeNode {
  id: number
  parent_id: number | null
  name: string
  leader_id: number | null
  sort_order: number
  children: DepartmentTreeNode[]
}

export interface RoleBrief {
  id: number
  role_name: string
  role_code: string
}

export interface RoleOut {
  id: number
  role_name: string
  role_code: string
  description: string | null
}

export interface UserOut {
  id: number
  username: string
  display_name: string | null
  department_id: number | null
  department_name: string | null
  status: number
  roles: RoleBrief[]
}

export interface PermissionItem {
  permission_code: string
  permission_type: string
}

// ---- 部门 ----
export const getDepartments = () =>
  client.get<DepartmentTreeNode[], DepartmentTreeNode[]>('/org/departments')

export const createDepartment = (data: {
  parent_id?: number | null
  name: string
  leader_id?: number | null
  sort_order?: number
}) => client.post<DepartmentTreeNode, DepartmentTreeNode>('/org/departments', data)

export const updateDepartment = (
  id: number,
  data: {
    parent_id?: number | null
    name?: string | null
    leader_id?: number | null
    sort_order?: number | null
  },
) => client.put<DepartmentTreeNode, DepartmentTreeNode>(`/org/departments/${id}`, data)

export const deleteDepartment = (id: number) =>
  client.delete<void, void>(`/org/departments/${id}`)

// ---- 用户 ----
export interface UserListParams {
  keyword?: string
  department_id?: number
  status?: number
  page?: number
  page_size?: number
}

export const getUsers = (params: UserListParams) =>
  client.get<PageResult<UserOut>, PageResult<UserOut>>('/org/users', { params })

export const getUser = (id: number) => client.get<UserOut, UserOut>(`/org/users/${id}`)

export const createUser = (data: {
  username: string
  password: string
  display_name?: string | null
  department_id?: number | null
  role_ids?: number[]
  status?: number
}) => client.post<UserOut, UserOut>('/org/users', data)

export const updateUser = (
  id: number,
  data: { display_name?: string | null; department_id?: number | null; role_ids?: number[] | null },
) => client.put<UserOut, UserOut>(`/org/users/${id}`, data)

export const resetPassword = (id: number, password: string) =>
  client.post<void, void>(`/org/users/${id}/password`, { password })

export const updateUserStatus = (id: number, status: number) =>
  client.patch<void, void>(`/org/users/${id}/status`, { status })

// ---- 角色 ----
export const getRoles = () => client.get<RoleOut[], RoleOut[]>('/org/roles')

export const createRole = (data: {
  role_name: string
  role_code: string
  description?: string | null
}) => client.post<RoleOut, RoleOut>('/org/roles', data)

export const updateRole = (
  id: number,
  data: { role_name?: string | null; description?: string | null },
) => client.put<RoleOut, RoleOut>(`/org/roles/${id}`, data)

export const deleteRole = (id: number) => client.delete<void, void>(`/org/roles/${id}`)

export const getRolePermissions = (id: number) =>
  client.get<PermissionItem[], PermissionItem[]>(`/org/roles/${id}/permissions`)

export const setRolePermissions = (id: number, permissions: PermissionItem[]) =>
  client.post<void, void>(`/org/roles/${id}/permissions`, { permissions })