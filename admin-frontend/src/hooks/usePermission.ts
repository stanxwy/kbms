import { useAuthStore } from '../store/auth'

/** 判断当前用户是否持有任一给定权限码（OR 语义，与服务端 require_permissions 对齐）。 */
export function hasPermission(permissions: string[], ...codes: string[]): boolean {
  if (codes.length === 0) return true
  return codes.some((code) => permissions.includes(code))
}

/**
 * 读取当前登录用户权限集的 hook。
 * 返回可用于菜单过滤、按钮显隐判断的权限集合与 `can` 判断函数。
 */
export function usePermission() {
  const permissions = useAuthStore((state) => state.permissions)
  return {
    permissions,
    can: (...codes: string[]) => hasPermission(permissions, ...codes),
  }
}