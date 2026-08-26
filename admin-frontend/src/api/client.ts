import axios from 'axios'

import { useAuthStore } from '../store/auth'

/** 统一 axios 实例：baseURL 指向 admin 后端 /api。 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 30000,
})

// 请求拦截：注入 JWT access token。
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：统一解包 {code, message, data}；401 时登出并跳登录页。
client.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 200) {
        return Promise.reject(new Error(body.message ?? '请求失败'))
      }
      return body.data
    }
    return body
  },
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default client