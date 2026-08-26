"""RAG 核心 HTTP 客户端。

封装 admin 对 RAG `/api/v1`（upload/recall/embed/query/stream/task/history）的调用，
统一超时、重试与错误处理。完整实现见实施任务分解 T2.1；P0 仅建立模块骨架。
"""