import { lazy, Suspense } from 'react'
import type { ReactElement } from 'react'
import { Navigate, createBrowserRouter } from 'react-router-dom'

import BasicLayout from '../layouts/BasicLayout'
import LoginPage from '../pages/login'
import { useAuthStore } from '../store/auth'
import { APP_MENU, filterMenu } from './menu'
import type { AppMenuItem } from './menu'

// 按页懒加载拆包：减少首屏 bundle，各页面独立为 chunk。
const DashboardPage = lazy(() => import('../pages/dashboard'))
const ChatPage = lazy(() => import('../pages/chat'))
const KnowledgePage = lazy(() => import('../pages/knowledge'))
const DepartmentsPage = lazy(() => import('../pages/org/departments'))
const RolesPage = lazy(() => import('../pages/org/roles'))
const UsersPage = lazy(() => import('../pages/org/users'))
const FaqsPage = lazy(() => import('../pages/settlement/faqs'))
const GapsPage = lazy(() => import('../pages/settlement/gaps'))

/** 页面加载过渡。 */
function PageFallback({ children }: { children: ReactElement }) {
  return <Suspense fallback={<div style={{ padding: 48, textAlign: 'center' }}>加载中…</div>}>{children}</Suspense>
}

/** 登录态守卫：无 token 时重定向登录页。 */
function RequireAuth({ children }: { children: ReactElement }) {
  const token = useAuthStore((state) => state.token)
  if (!token) return <Navigate to="/login" replace />
  return children
}

/** 返回菜单树中第一个叶子路径（跳转落地页用）。 */
function firstLeafPath(menus: AppMenuItem[]): string | null {
  for (const item of menus) {
    if (item.children && item.children.length > 0) {
      const p = firstLeafPath(item.children)
      if (p) return p
    } else {
      return item.path
    }
  }
  return null
}

/** 登录后默认落地页：跳转用户第一个有权限的菜单。 */
function DefaultIndex() {
  const permissions = useAuthStore((state) => state.permissions)
  const first = firstLeafPath(filterMenu(APP_MENU, permissions))
  return <Navigate to={first ?? '/dashboard'} replace />
}

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <BasicLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DefaultIndex /> },
      { path: 'dashboard', element: <PageFallback><DashboardPage /></PageFallback> },
      { path: 'org/users', element: <PageFallback><UsersPage /></PageFallback> },
      { path: 'org/roles', element: <PageFallback><RolesPage /></PageFallback> },
      { path: 'org/departments', element: <PageFallback><DepartmentsPage /></PageFallback> },
      { path: 'knowledge', element: <PageFallback><KnowledgePage /></PageFallback> },
      { path: 'chat', element: <PageFallback><ChatPage /></PageFallback> },
      { path: 'settlement/faqs', element: <PageFallback><FaqsPage /></PageFallback> },
      { path: 'settlement/gaps', element: <PageFallback><GapsPage /></PageFallback> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])