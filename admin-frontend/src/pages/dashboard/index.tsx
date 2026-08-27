import { useEffect, useState } from 'react'
import { Card, Col, Empty, Row, Segmented, Spin, Statistic, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

import {
  getAccessStats,
  getMetrics,
  getQuestionRanking,
  getTokenStats,
  getUnitRanking,
  type AccessTrendPoint,
  type DashboardMetrics,
  type Granularity,
  type QuestionRankItem,
  type TokenTrendPoint,
  type UnitRankItem,
} from '../../api/dashboard'

/** 看板核心指标卡片 + 榜单 + 趋势图（echarts-for-react）。 */
export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [questions, setQuestions] = useState<QuestionRankItem[]>([])
  const [units, setUnits] = useState<UnitRankItem[]>([])
  const [tokenTrend, setTokenTrend] = useState<TokenTrendPoint[]>([])
  const [accessTrend, setAccessTrend] = useState<AccessTrendPoint[]>([])
  const [granularity, setGranularity] = useState<Granularity>('day')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([getMetrics(), getQuestionRanking(10), getUnitRanking(10)])
      .then(([m, q, u]) => {
        if (cancelled) return
        setMetrics(m)
        setQuestions(q)
        setUnits(u)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.all([getTokenStats(granularity, 30), getAccessStats(granularity, 30)])
      .then(([t, a]) => {
        if (cancelled) return
        setTokenTrend(t)
        setAccessTrend(a)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [granularity])

  const tokenOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Token 消耗', '平均响应时间(ms)'] },
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: tokenTrend.map((t) => t.bucket) },
    yAxis: [
      { type: 'value', name: 'Token' },
      { type: 'value', name: '响应(ms)' },
    ],
    series: [
      {
        name: 'Token 消耗',
        type: 'line',
        smooth: true,
        data: tokenTrend.map((t) => t.total_tokens),
      },
      {
        name: '平均响应时间(ms)',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: tokenTrend.map((t) => t.avg_response_time_ms),
      },
    ],
  }

  const accessOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['访问量', '独立用户'] },
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: accessTrend.map((a) => a.bucket) },
    yAxis: { type: 'value' },
    series: [
      { name: '访问量', type: 'line', smooth: true, data: accessTrend.map((a) => a.access_count) },
      { name: '独立用户', type: 'line', smooth: true, data: accessTrend.map((a) => a.uv) },
    ],
  }

  const questionOption: EChartsOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      inverse: true,
      data: questions.map((q) => q.question),
      axisLabel: { width: 160, overflow: 'truncate' },
    },
    series: [{ type: 'bar', data: questions.map((q) => q.count), barMaxWidth: 16 }],
  }

  const unitColumns: ColumnsType<UnitRankItem> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (_, r) => r.title ?? r.source_file_name ?? `#${r.unit_id}`,
    },
    { title: '访问次数', dataIndex: 'count', key: 'count', width: 100 },
  ]

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic title="总访问量" value={metrics?.access_count ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="独立用户" value={metrics?.uv ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="知识单元" value={metrics?.unit_count ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Token 消耗" value={metrics?.total_tokens ?? 0} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={4}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Segmented
              block
              value={granularity}
              onChange={(v) => setGranularity(v as Granularity)}
              options={[
                { label: '按日', value: 'day' },
                { label: '按周', value: 'week' },
              ]}
            />
          </Card>
          <Card title="平均响应时间" size="small" style={{ marginBottom: 16 }}>
            <Statistic
              value={metrics?.avg_response_time_ms ?? 0}
              suffix="ms"
              precision={0}
            />
          </Card>
        </Col>
        <Col span={20}>
          <Card title="访问趋势" style={{ marginBottom: 16 }}>
            {accessTrend.length === 0 ? (
              <Empty description="暂无趋势数据" />
            ) : (
              <ReactECharts option={accessOption} style={{ height: 280 }} />
            )}
          </Card>
          <Card title="Token 与响应时间趋势">
            {tokenTrend.length === 0 ? (
              <Empty description="暂无趋势数据" />
            ) : (
              <ReactECharts option={tokenOption} style={{ height: 280 }} />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={14}>
          <Card title="高频问题榜">
            {questions.length === 0 ? (
              <Empty description="暂无数据" />
            ) : (
              <ReactECharts option={questionOption} style={{ height: 320 }} />
            )}
          </Card>
        </Col>
        <Col span={10}>
          <Card title="最常访问知识单元">
            <Table
              rowKey="unit_id"
              size="small"
              columns={unitColumns}
              dataSource={units}
              pagination={false}
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  )
}