import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, List, Tag, Progress, Spin, Empty, Space } from 'antd';
import { BookOutlined, FileTextOutlined, TeamOutlined, EyeOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import { chapterApi, memoryApi, graphStatusApi } from '../services/api';

const { Title, Text } = Typography;

export default function Dashboard() {
  const { currentProject, chapters, characters, setChapters } = useStore();
  const [loading, setLoading] = useState(false);
  const [graphState, setGraphState] = useState<any>(null);
  const [recentMemories, setRecentMemories] = useState<any[]>([]);
  const navigate = useNavigate();
  const projectId = currentProject?.id || '';

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [chData, gState, memData]: any[] = await Promise.all([
        chapterApi.list(projectId),
        graphStatusApi.getState(projectId),
        memoryApi.list(projectId),
      ]);
      setChapters(chData.items || []);
      setGraphState(gState);
      setRecentMemories((memData.items || []).slice(0, 5));
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [projectId]);

  const totalWords = chapters.reduce((sum: number, ch: any) => sum + (ch.word_count || 0), 0);
  const completedChapters = chapters.filter((ch: any) => ch.status === 'final' || ch.status === 'polished').length;

  if (!currentProject) {
    return <Empty description="请先选择一个项目" />;
  }

  return (
    <div>
      <Title level={4}><BookOutlined style={{ marginRight: 8 }} />{currentProject.title}</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>{currentProject.description}</Text>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {[
            { title: '总字数', value: totalWords.toLocaleString(), icon: <FileTextOutlined />, color: '#1890ff' },
            { title: '章节数', value: `${completedChapters}/${chapters.length}`, icon: <BookOutlined />, color: '#52c41a' },
            { title: '角色数', value: characters.length, icon: <TeamOutlined />, color: '#fa8c16' },
            { title: '当前阶段', value: graphState?.current_phase || 'planning', icon: <EyeOutlined />, color: '#722ed1' },
          ].map((s) => (
            <Col xs={12} sm={6} key={s.title}>
              <Card><Statistic title={s.title} value={s.value} prefix={s.icon} valueStyle={{ color: s.color }} /></Card>
            </Col>
          ))}
        </Row>

        <Row gutter={16}>
          <Col xs={24} lg={12}>
            <Card title="章节进度" extra={<a onClick={() => navigate('chapters')}>查看全部 <ArrowRightOutlined /></a>}>
              {chapters.length === 0 ? <Empty description="暂无章节" /> : (
                <List size="small" dataSource={chapters.slice(0, 8)}
                  renderItem={(ch: any) => (
                    <List.Item>
                      <Space>
                        <Tag color={ch.status === 'final' ? 'green' : ch.status === 'polished' ? 'blue' : 'default'}>
                          {ch.status}
                        </Tag>
                        <Text>第{ch.chapter_index}章 {ch.title}</Text>
                        <Text type="secondary">{ch.word_count?.toLocaleString()}字</Text>
                      </Space>
                    </List.Item>
                  )} />
              )}
              {chapters.length > 0 && (
                <Progress percent={Math.round((completedChapters / chapters.length) * 100)}
                  style={{ marginTop: 16 }} />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="近期记忆" extra={<a onClick={() => navigate('memories')}>查看全部 <ArrowRightOutlined /></a>}>
              {recentMemories.length === 0 ? <Empty description="暂无记忆" /> : (
                <List size="small" dataSource={recentMemories}
                  renderItem={(m: any) => (
                    <List.Item>
                      <Space>
                        <Tag>{m.memory_type || '记忆'}</Tag>
                        <Text ellipsis style={{ maxWidth: 300 }}>{m.summary || m.content || ''}</Text>
                      </Space>
                    </List.Item>
                  )} />
              )}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
}
