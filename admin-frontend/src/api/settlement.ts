import client from './client'
import type { PageResult } from './types'

// ---- 类型定义（对齐后端 schemas/settlement.py） ----

export interface FAQItem {
  id: number
  question: string
  answer: string
  category: string | null
  related_unit_id: number | null
  source_type: string
  status: string
  hit_count: number
  reviewer_id: number | null
  reviewed_at: string | null
}

export interface KnowledgeGapItem {
  id: number
  question_pattern: string
  sample_questions: string[]
  ask_count: number
  last_asked_at: string | null
  status: string
  resolved_unit_id: number | null
}

export interface FAQListParams {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}

// ---- FAQ ----
export const getFaqRecommendations = (page = 1, page_size = 20) =>
  client.get<PageResult<FAQItem>, PageResult<FAQItem>>('/settlement/faqs/recommendations', {
    params: { page, page_size },
  })

export const reviewFaq = (
  id: number,
  data: { action: 'approve' | 'reject'; edited_answer?: string; category?: string },
) => client.post<FAQItem, FAQItem>(`/settlement/faqs/${id}/review`, data)

export const getFaqs = (params: FAQListParams) =>
  client.get<PageResult<FAQItem>, PageResult<FAQItem>>('/settlement/faqs', { params })

export const updateFaq = (
  id: number,
  data: {
    question?: string
    answer?: string
    category?: string | null
    related_unit_id?: number | null
  },
) => client.put<FAQItem, FAQItem>(`/settlement/faqs/${id}`, data)

export const deleteFaq = (id: number) => client.delete<void, void>(`/settlement/faqs/${id}`)

// ---- 知识缺口 ----
export const getKnowledgeGaps = (params: FAQListParams) =>
  client.get<PageResult<KnowledgeGapItem>, PageResult<KnowledgeGapItem>>(
    '/settlement/knowledge-gaps',
    { params },
  )

export const resolveGap = (
  id: number,
  data: { title?: string; content?: string; category?: string },
) => client.post<KnowledgeGapItem, KnowledgeGapItem>(`/settlement/knowledge-gaps/${id}/resolve`, data)

export const ignoreGap = (id: number) =>
  client.patch<void, void>(`/settlement/knowledge-gaps/${id}/ignore`)