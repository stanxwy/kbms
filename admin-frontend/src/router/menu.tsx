import type { ReactNode } from 'react'
import {
  ApartmentOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  MessageOutlined,
} from '@ant-design/icons'

import { hasPermission } from '../hooks/usePermission'

/** 前端菜单项：path 作为路由 key，permission 为显隐所需的权限码（任一命中即可，父级可省略）。 */
export interface AppMenuItem {
  path: string
  label: string
  icon?: ReactNode
  permission?: string[]
  children?: AppMenuItem[]
}

/** 菜单树（对应后端权限码全集，父级权限由子级聚合）。 */
export const APP_MENU: AppMenuItem[] = [
  { path: '/dashboard', label: '数据看板', icon: <DashboardOutlined />, permission: ['menu:dashboard'] },
  {
    path: '/org',
    label: '组织架构',
    icon: <ApartmentOutlined />,
    children: [
      { path: '/org/users', label: '用户管理', permission: ['menu:org:user'] },
      { path: '/org/roles', label: '角色管理', permission: ['menu:org:role'] },
      { path: '/org/departments', label: '部门管理', permission: ['menu:org:dept'] },
    ],
  },
  {
    path: '/knowledge',
    label: '知识维护',
    icon: <FileTextOutlined />,
    permission: ['op:knowledge:unit:read'],
  },
  { path: '/chat', label: 'AI 对话', icon: <MessageOutlined />, permission: ['op:ai:chat'] },
  {
    path: '/settlement',
    label: '知识沉淀',
    icon: <ExperimentOutlined />,
    children: [
      { path: '/settlement/faqs', label: 'FAQ 管理', permission: ['menu:settlement:faq'] },
      { path: '/settlement/gaps', label: '知识缺口', permission: ['menu:settlement:gap'] },
    ],
  },
]

/** 按用户权限过滤菜单：父级若所有子项均被过滤则一并隐藏。 */
export function filterMenu(menu: AppMenuItem[], permissions: string[]): AppMenuItem[] {
  const result: AppMenuItem[] = []
  for (const item of menu) {
    const children = item.children ? filterMenu(item.children, permissions) : undefined
    const selfAllowed = item.permission ? hasPermission(permissions, ...item.permission) : true
    if (item.children) {
      if (children && children.length > 0) {
        result.push({ ...item, children })
      }
    } else if (selfAllowed) {
      result.push(item)
    }
  }
  return result
}