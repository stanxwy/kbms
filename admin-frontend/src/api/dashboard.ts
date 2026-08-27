import client from './client'

// ---- 类型定义（对齐后端 schemas/dashboard.py） ----

export interface DashboardMetrics {
  access_count: number
  uv: number
  unit_count: number
  total_tokens: number
  avg_response_time_ms: number
}

export interface QuestionRankItem {
  question: string
  count: number
}

export interface UnitRankItem {
  unit_id: number
  title: string | null
  source_file_name: string | null
  count: number
}

export interface TokenTrendPoint {
  bucket: string
  total_tokens: number
  avg_response_time_ms: number
}

export interface AccessTrendPoint {
  bucket: string
  access_count: number
  uv: number
}

export type Granularity = 'day' | 'week'

export const getMetrics = () =>
  client.get<DashboardMetrics, DashboardMetrics>('/dashboard/metrics')

export const getQuestionRanking = (limit = 10) =>
  client.get<QuestionRankItem[], QuestionRankItem[]>('/dashboard/rankings/questions', {
    params: { limit },
  })

export const getUnitRanking = (limit = 10) =>
  client.get<UnitRankItem[], UnitRankItem[]>('/dashboard/rankings/units', {
    params: { limit },
  })

export const getTokenStats = (granularity: Granularity = 'day', days = 30) =>
  client.get<TokenTrendPoint[], TokenTrendPoint[]>('/dashboard/stats/tokens', {
    params: { granularity, days },
  })

export const getAccessStats = (granularity: Granularity = 'day', days = 30) =>
  client.get<AccessTrendPoint[], AccessTrendPoint[]>('/dashboard/stats/access', {
    params: { granularity, days },
  })