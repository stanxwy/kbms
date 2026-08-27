/** 统一分页响应（对应后端 PageResult）。 */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 分页查询公共参数。 */
export interface PageQuery {
  page?: number
  page_size?: number
}