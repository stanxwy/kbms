import { Card, Empty } from 'antd'

export default function DashboardPage() {
  return (
    <Card title="数据看板">
      <Empty description="看板数据将在 T5（数据看板）阶段接入" />
    </Card>
  )
}