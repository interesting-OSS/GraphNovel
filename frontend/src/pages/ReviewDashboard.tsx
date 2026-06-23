import { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Tag, Space, List, Empty, Spin, Select, Button, Alert, Statistic } from 'antd';
import {
  AuditOutlined, CheckCircleOutlined,
  ThunderboltOutlined, ReadOutlined, BulbOutlined, DashboardOutlined,
} from '@ant-design/icons';
import { useStore } from '../store';
import { chapterExtendedApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

interface ReviewResult {
  reader_review?: { score: number; strengths: string[]; weaknesses: string[]; suggestions: string[] };
  logic_check?: { score: number; issues: string[]; timeline_ok: boolean };
  prose_check?: { score: number; issues: string[]; highlights: string[] };
  pacing_check?: { score: number; rhythm_curve: string; suggestions: string[] };
  aggregate?: { overall_score: number; summary: string; priority_actions: string[] };
}

export default function ReviewDashboard() {
  const { currentProject, chapters } = useStore();
  const [chapterId, setChapterId] = useState('');
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState<ReviewResult | null>(null);
  const projectId = currentProject?.id || '';

  const handleRunReview = async () => {
    if (!projectId || !chapterId) return;
    setLoading(true);
    setReview(null);
    try {
      const data: any = await chapterExtendedApi.review(chapterId);
      if (data) setReview(data as ReviewResult);
    } catch { /* handled by interceptor */ }
    finally { setLoading(false); }
  };

  const scoreColor = (s: number) => (s >= 8 ? '#52c41a' : s >= 6 ? '#fa8c16' : '#f5222d');

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}><AuditOutlined style={{ marginRight: 8 }} />多 Agent 智能审稿</Title>
        <Space>
          <Select showSearch placeholder="选择要审阅的章节" value={chapterId || undefined}
            onChange={setChapterId} style={{ width: 280 }}
            options={chapters.map((ch: any) => ({
              value: ch.id, label: `第${ch.chapter_index}章 ${ch.title}`,
            }))}
            filterOption={(input, option) => (option?.label as string)?.includes(input)} />
          <Button type="primary" icon={<ThunderboltOutlined />}
            onClick={handleRunReview} loading={loading} disabled={!chapterId}>
            开始审稿
          </Button>
        </Space>
      </div>

      <Spin spinning={loading} tip="4 个 Agent 并行审阅中...">
        {!review ? (
          <Empty description="选择章节后点击「开始审稿」，4 个专职 Agent 将并行审阅" style={{ marginTop: 80 }}>
            <Space direction="vertical">
              <Text type="secondary">👁️ 读者视角 Agent — 从读者体验角度审阅</Text>
              <Text type="secondary">🔍 逻辑检查 Agent — 检查情节一致性和时间线</Text>
              <Text type="secondary">✍️ 文笔检查 Agent — 分析用词、句式、描写比例</Text>
              <Text type="secondary">⏱️ 节奏分析 Agent — 评估章节内张弛节奏</Text>
            </Space>
          </Empty>
        ) : (
          <>
            {/* Overall score */}
            {review.aggregate && (
              <Card style={{ marginBottom: 16, textAlign: 'center', background: '#f6ffed' }}>
                <Statistic title="综合评分" value={review.aggregate.overall_score} suffix="/ 10"
                  valueStyle={{ color: scoreColor(review.aggregate.overall_score), fontSize: 36 }} />
                <Paragraph style={{ marginTop: 8 }}>{review.aggregate.summary}</Paragraph>
                {review.aggregate.priority_actions && (
                  <Space wrap>
                    {review.aggregate.priority_actions.map((a, i) => (
                      <Alert key={i} message={a} type="warning" showIcon style={{ marginTop: 4 }} />
                    ))}
                  </Space>
                )}
              </Card>
            )}

            <Row gutter={[16, 16]}>
              {/* Reader Review */}
              {review.reader_review && (
                <Col xs={24} lg={12}>
                  <Card title={<span><ReadOutlined /> 读者视角</span>}
                    extra={<Tag color={review.reader_review.score >= 7 ? 'green' : 'orange'}>
                      评分: {review.reader_review.score}</Tag>}>
                    <Text strong>优点：</Text>
                    <List size="small" dataSource={review.reader_review.strengths || []}
                      renderItem={(s: string) => <List.Item>✅ {s}</List.Item>} />
                    <Text strong>问题：</Text>
                    <List size="small" dataSource={review.reader_review.weaknesses || []}
                      renderItem={(w: string) => <List.Item>⚠️ {w}</List.Item>} />
                  </Card>
                </Col>
              )}

              {/* Logic Check */}
              {review.logic_check && (
                <Col xs={24} lg={12}>
                  <Card title={<span><CheckCircleOutlined /> 逻辑一致性</span>}
                    extra={<Tag color={review.logic_check.timeline_ok ? 'green' : 'red'}>
                      {review.logic_check.timeline_ok ? '时间线正常' : '时间线异常'}</Tag>}>
                    <List size="small" dataSource={review.logic_check.issues || []}
                      renderItem={(s: string) => <List.Item>🔍 {s}</List.Item>} />
                  </Card>
                </Col>
              )}

              {/* Prose Check */}
              {review.prose_check && (
                <Col xs={24} lg={12}>
                  <Card title={<span><BulbOutlined /> 文笔质量</span>}
                    extra={<Tag color="blue">评分: {review.prose_check.score}</Tag>}>
                    <Text strong>亮点：</Text>
                    <List size="small" dataSource={review.prose_check.highlights || []}
                      renderItem={(h: string) => <List.Item>✨ {h}</List.Item>} />
                    <Text strong>可改进：</Text>
                    <List size="small" dataSource={review.prose_check.issues || []}
                      renderItem={(i: string) => <List.Item>📝 {i}</List.Item>} />
                  </Card>
                </Col>
              )}

              {/* Pacing Check */}
              {review.pacing_check && (
                <Col xs={24} lg={12}>
                  <Card title={<span><DashboardOutlined /> 节奏分析</span>}
                    extra={<Tag color="purple">评分: {review.pacing_check.score}</Tag>}>
                    <Text>节奏曲线: {review.pacing_check.rhythm_curve}</Text>
                    <List size="small" dataSource={review.pacing_check.suggestions || []}
                      renderItem={(s: string) => <List.Item>💡 {s}</List.Item>} />
                  </Card>
                </Col>
              )}
            </Row>
          </>
        )}
      </Spin>
    </div>
  );
}
