import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  department_id: number | null
}

interface AuthState {
  token: string
  refreshToken: string
  user: UserInfo | null
  permissions: string[]
  setAuth: (token: string, refreshToken: string, user: UserInfo, permissions: string[]) => void
  setPermissions: (permissions: string[]) => void
  logout: () => void
}

/** 认证态：token / 用户信息 / 操作权限码，持久化到 localStorage。 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: '',
      refreshToken: '',
      user: null,
      permissions: [],
      setAuth: (token, refreshToken, user, permissions) =>
        set({ token, refreshToken, user, permissions }),
      setPermissions: (permissions) => set({ permissions }),
      logout: () => set({ token: '', refreshToken: '', user: null, permissions: [] }),
    }),
    { name: 'kbms-auth' },
  ),
)