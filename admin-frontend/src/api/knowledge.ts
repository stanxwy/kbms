import client from './client'
import type { PageResult } from './types'

// ---- 类型定义（对齐后端 schemas/knowledge.py） ----

export interface UnitPermissionItem {
  target_type: 'global' | 'department' | 'role' | 'user'
  target_id: number
}

export interface KnowledgeUnitOut {
  id: number
  unit_code: string
  title: string
  content: string | null
  summary: string | null
  category: string | null
  source_file_name: string
  file_type: string
  file_size: number
  status: string
  creator_id: number | null
}

export interface KnowledgeUnitDetail extends KnowledgeUnitOut {
  permissions: UnitPermissionItem[]
}

export interface UnitListParams {
  keyword?: string
  category?: string
  status?: string
  file_type?: string
  page?: number
  page_size?: number
}

// ---- 导入 ----
export const importKnowledge = (files: File[]) => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return client.post<{ task_ids: string[] }, { task_ids: string[] }>('/knowledge/import', form)
}

export const getImportTask = (taskId: string) =>
  client.get<Record<string, unknown>, Record<string, unknown>>(`/knowledge/import/tasks/${taskId}`)

// ---- 知识单元 ----
export const getUnits = (params: UnitListParams) =>
  client.get<PageResult<KnowledgeUnitOut>, PageResult<KnowledgeUnitOut>>('/knowledge/units', {
    params,
  })

export const getUnit = (id: number) =>
  client.get<KnowledgeUnitDetail, KnowledgeUnitDetail>(`/knowledge/units/${id}`)

export const updateUnit = (
  id: number,
  data: {
    title?: string | null
    content?: string | null
    summary?: string | null
    category?: string | null
    status?: string | null
  },
) => client.put<KnowledgeUnitOut, KnowledgeUnitOut>(`/knowledge/units/${id}`, data)

export const deleteUnits = (ids: number[]) =>
  client.delete<void, void>('/knowledge/units', { data: { ids } })

// ---- 数据权限 ----
export const getUnitPermissions = (id: number) =>
  client.get<UnitPermissionItem[], UnitPermissionItem[]>(`/knowledge/units/${id}/permissions`)

export const setUnitPermissions = (id: number, permissions: UnitPermissionItem[]) =>
  client.post<void, void>(`/knowledge/units/${id}/permissions`, { permissions })