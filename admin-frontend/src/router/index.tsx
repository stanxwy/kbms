import type { ReactElement } from 'react'
import { Navigate, createBrowserRouter } from 'react-router-dom'

import BasicLayout from '../layouts/BasicLayout'
import DashboardPage from '../pages/dashboard'
import LoginPage from '../pages/login'
import { useAuthStore } from '../store/auth'

/** 登录态守卫占位：无 token 时重定向登录页（T7.1 完善 token 刷新/失效处理）。 */
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
    children: [{ index: true, element: <DashboardPage /> }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])