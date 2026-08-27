import type { ReactElement } from 'react'
import { Navigate, createBrowserRouter } from 'react-router-dom'

import BasicLayout from '../layouts/BasicLayout'
import DashboardPage from '../pages/dashboard'
import ChatPage from '../pages/chat'
import KnowledgePage from '../pages/knowledge'
import DepartmentsPage from '../pages/org/departments'
import RolesPage from '../pages/org/roles'
import UsersPage from '../pages/org/users'
import FaqsPage from '../pages/settlement/faqs'
import GapsPage from '../pages/settlement/gaps'
import LoginPage from '../pages/login'
import { useAuthStore } from '../store/auth'

/** 登录态守卫：无 token 时重定向登录页。 */
function RequireAuth({ children }: { children: ReactElement }) {
  const token = useAuthStore((state) => state.token)
  if (!token) return <Navigate to="/login" replace />
  return children
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
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'org/users', element: <UsersPage /> },
      { path: 'org/roles', element: <RolesPage /> },
      { path: 'org/departments', element: <DepartmentsPage /> },
      { path: 'knowledge', element: <KnowledgePage /> },
      { path: 'chat', element: <ChatPage /> },
      { path: 'settlement/faqs', element: <FaqsPage /> },
      { path: 'settlement/gaps', element: <GapsPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])