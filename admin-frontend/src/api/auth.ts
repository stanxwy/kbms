import client from './client'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  user_info: {
    id: number
    username: string
    display_name: string
    department_id: number | null
  }
  permissions: string[]
}

/** 登录（POST /api/auth/login）。 */
export const login = (params: LoginParams) =>
  client.post<LoginResult, LoginResult>('/auth/login', params)

/** 登出（POST /api/auth/logout）。 */
export const logout = () => client.post('/auth/logout')

/** 当前用户（GET /api/auth/me）。 */
export const getMe = () => client.get('/auth/me')