import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Row, Col, Tag, Spin, Empty, Typography, Space, theme } from 'antd';
import { PlusOutlined, BookOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useProjectSync } from '../store/hooks';
import { useStore } from '../store';
import type { Project } from '../types';

const { Title, Text, Paragraph } = Typography;

export default function ProjectList() {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { projects } = useStore();
  const { refreshProjects, deleteProject } = useProjectSync();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    refreshProjects().finally(() => setLoading(false));
  }, [refreshProjects]);

  const statusMap: Record<string, { color: string; label: string }> = {
    planning: { color: 'blue', label: '规划中' },
    writing: { color: 'orange', label: '创作中' },
    revising: { color: 'purple', label: '修订中' },
    completed: { color: 'green', label: '已完成' },
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <BookOutlined style={{ marginRight: 8 }} />
          我的小说
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/wizard')}>
          创建新项目
        </Button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>
      ) : projects.length === 0 ? (
        <Empty description="还没有小说项目，点击上方按钮开始创作" style={{ padding: 60 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/wizard')}>
            创建第一个项目
          </Button>
        </Empty>
      ) : (
        <Row gutter={[16, 16]}>
          {projects.map((project: Project) => {
            const status = statusMap[project.status] || statusMap.planning;
            return (
              <Col xs={24} sm={12} lg={8} key={project.id}>
                <Card
                  hoverable
                  onClick={() => navigate(`/project/${project.id}`)}
                  actions={[
                    <EditOutlined key="edit" onClick={(e) => { e.stopPropagation(); navigate(`/project/${project.id}/world-setting`); }} />,
                    <DeleteOutlined key="delete" onClick={(e) => {
                      e.stopPropagation();
                      deleteProject(project.id);
                    }} />,
                  ]}
                  cover={
                    project.cover_url ? (
                      <img alt={project.title} src={project.cover_url} style={{ height: 180, objectFit: 'cover' }} />
                    ) : (
                      <div style={{
                        height: 180,
                        background: `linear-gradient(135deg, ${token.colorPrimary}40, ${token.colorPrimary}20)`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <BookOutlined style={{ fontSize: 48, color: token.colorPrimary }} />
                      </div>
                    )
                  }
                  style={{ height: '100%' }}
                >
                  <Card.Meta
                    title={
                      <Space>
                        {project.title}
                        <Tag color={status.color}>{status.label}</Tag>
                      </Space>
                    }
                    description={
                      <>
                        <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}>
                          {project.description || '暂无简介'}
                        </Paragraph>
                        <Space size={12}>
                          <Tag>{project.genre}</Tag>
                          <Text type="secondary">{project.total_word_count.toLocaleString()} 字</Text>
                        </Space>
                      </>
                    }
                  />
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </div>
  );
}
