import { Alert, Space, Tag, Typography } from 'antd'
import type { SourceItem, UnauthorizedItem } from '../api/ai'

interface SourceCiteCardProps {
  sources: SourceItem[]
  unauthorized: UnauthorizedItem[]
}

/** 问答引用来源卡片 + 无权限召回项缺失提示。 */
export default function SourceCiteCard({ sources, unauthorized }: SourceCiteCardProps) {
  if (sources.length === 0 && unauthorized.length === 0) return null
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={8}>
      {sources.length > 0 && (
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            知识来源：
          </Typography.Text>
          <Space size={4} wrap>
            {sources.map((s) => (
              <Tag key={s.unit_id} color="blue">
                {s.title}
              </Tag>
            ))}
          </Space>
        </div>
      )}
      {unauthorized.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message="部分相关内容无访问权限"
          description={unauthorized.map((u) => u.title).join('、')}
        />
      )}
    </Space>
  )
}