import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Tag, Progress, List, Empty, Spin, Select, Space, Divider } from 'antd';
import { BarChartOutlined, ThunderboltOutlined, SmileOutlined, DashboardOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useStore } from '../store';
import { memoryApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

export default function ChapterAnalysis() {
  const { currentProject, chapters } = useStore();
  const [selectedChapterId, setSelectedChapterId] = useState('');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const projectId = currentProject?.id || '';

  useEffect(() => {
    if (chapters.length > 0 && !selectedChapterId) {
      setSelectedChapterId(chapters[chapters.length - 1].id);
    }
  }, [chapters]);

  useEffect(() => {
    if (!projectId || !selectedChapterId) return;
    setLoading(true);
    memoryApi.getAnalysis(projectId, selectedChapterId)
      .then((data: any) => setAnalysis(data))
      .catch(() => setAnalysis(null))
      .finally(() => setLoading(false));
  }, [projectId, selectedChapterId]);

  const parseJSON = (raw: any, fallback: any = null) => {
    if (!raw) return fallback;
    if (typeof raw === 'object') return raw;
    try { return JSON.parse(raw); } catch { return fallback; }
  };

  const plotPoints = parseJSON(analysis?.plot_points, []);
  const conflictInfo = parseJSON(analysis?.conflict_info, {});
  const emotionalArc = parseJSON(analysis?.emotional_arc, {});
  const suggestions = parseJSON(analysis?.suggestions, []);

  return (
    <div>
      <Title level={4}><BarChartOutlined style={{ marginRight: 8 }} />章节分析</Title>

      <Space style={{ marginBottom: 16 }}>
        <Select showSearch placeholder="选择章节" value={selectedChapterId || undefined}
          onChange={setSelectedChapterId} style={{ width: 320 }}
          options={chapters.map((ch: any) => ({
            value: ch.id,
            label: `第${ch.chapter_index}章 ${ch.title}`,
          }))}
          filterOption={(input, option) => (option?.label as string)?.includes(input)} />
      </Space>

      <Spin spinning={loading}>
        {!analysis ? (
          <Empty description={loading ? '加载中...' : '该章节尚未分析，先生成内容后点击分析'} />
        ) : (
          <>
            {/* Score cards */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              {[
                { title: '节奏评分', value: analysis.pacing_score, color: '#1890ff', max: 10 },
                { title: '参与度', value: analysis.engagement_score, color: '#52c41a', max: 10 },
                { title: '连贯性', value: analysis.coherence_score, color: '#fa8c16', max: 10 },
                { title: '综合质量', value: analysis.quality_score, color: '#722ed1', max: 10 },
              ].map((s) => (
                <Col xs={12} sm={6} key={s.title}>
                  <Card size="small">
                    <Statistic title={s.title} value={s.value || '-'}
                      suffix={s.value ? `/ ${s.max}` : ''}
                      valueStyle={{ color: s.color, fontSize: 24 }} />
                    <Progress percent={((s.value || 0) / s.max) * 100} showInfo={false}
                      strokeColor={s.color} size="small" />
                  </Card>
                </Col>
              ))}
            </Row>

            {/* Proportions */}
            {analysis.dialogue_ratio != null && (
              <Row gutter={16} style={{ marginBottom: 24 }}>
                {[
                  { label: '对话占比', value: analysis.dialogue_ratio, color: '#1890ff' },
                  { label: '描写占比', value: analysis.description_ratio, color: '#52c41a' },
                  { label: '叙事占比', value: analysis.narrative_ratio, color: '#fa8c16' },
                ].map((p) => (
                  <Col xs={8} key={p.label}>
                    <Text>{p.label}</Text>
                    <Progress percent={Math.round((p.value || 0) * 100)} strokeColor={p.color} />
                  </Col>
                ))}
              </Row>
            )}

            <Row gutter={16}>
              <Col xs={24} lg={12}>
                {/* Plot points */}
                <Card title="情节要点" size="small" style={{ marginBottom: 16 }}>
                  {plotPoints.length === 0 ? <Empty description="无" /> : (
                    plotPoints.map((p: any, i: number) => (
                      <Tag key={i} color="blue" style={{ marginBottom: 4 }}>
                        {p.description || p}
                        {p.importance && <span> ★{Math.round(p.importance * 10)}</span>}
                      </Tag>
                    ))
                  )}
                </Card>

                {/* Conflict info */}
                <Card title="冲突分析" size="small" style={{ marginBottom: 16 }}>
                  {!conflictInfo?.type ? <Empty description="无明显冲突" /> : (
                    <Space direction="vertical">
                      <Text>类型: {conflictInfo.type}</Text>
                      {conflictInfo.participants && (
                        <Space wrap>
                          {conflictInfo.participants.map((p: string, i: number) => (
                            <Tag key={i}>{p}</Tag>
                          ))}
                        </Space>
                      )}
                      <Progress percent={(conflictInfo.resolution_progress || 0) * 100}
                        format={() => `解决进度: ${Math.round((conflictInfo.resolution_progress || 0) * 100)}%`} />
                    </Space>
                  )}
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                {/* Emotional arc */}
                <Card title="情感弧线" size="small" style={{ marginBottom: 16 }}>
                  {!emotionalArc?.primary_emotion ? <Empty description="无" /> : (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <SmileOutlined />
                        <Tag color="orange">{emotionalArc.primary_emotion}</Tag>
                        <Text>强度: {emotionalArc.intensity}</Text>
                      </Space>
                      {emotionalArc.trajectory && <Text>走向: {emotionalArc.trajectory}</Text>}
                      <Progress percent={(emotionalArc.intensity || 0) * 100}
                        strokeColor="#fa8c16" size="small" />
                    </Space>
                  )}
                </Card>

                {/* Suggestions */}
                <Card title="改进建议" size="small">
                  {suggestions.length === 0 ? <Empty description="无" /> : (
                    <List size="small" dataSource={suggestions}
                      renderItem={(s: string, i: number) => (
                        <List.Item><Text type="secondary">{i + 1}. {s}</Text></List.Item>
                      )} />
                  )}
                </Card>
              </Col>
            </Row>

            {/* Analysis Report */}
            {analysis.report && (
              <Card title="综合分析报告" style={{ marginTop: 16 }}>
                <div className="markdown-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {analysis.report}
                  </ReactMarkdown>
                </div>
              </Card>
            )}
          </>
        )}
      </Spin>
    </div>
  );
}
