import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Modal, Input, Empty, Spin, message } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, CrownOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { careerApi } from '../services/api';
import type { Career } from '../types';

const { Title, Text, Paragraph } = Typography;

export default function CareerManager() {
  const { currentProject, careers, setCareers } = useStore();
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<Career> | null>(null);
  const projectId = currentProject?.id || '';

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data: any = await careerApi.list(projectId);
      setCareers(data.items || []);
    } catch { /* interceptor handles toast */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [projectId]);

  const handleSave = async () => {
    if (!editing?.name) return;
    const data = { ...editing, project_id: projectId };
    if (editing.id) await careerApi.update(editing.id, data);
    else await careerApi.create(data);
    message.success('职业已保存');
    setEditOpen(false);
    load();
  };

  const handleDelete = async (id: string) => {
    await careerApi.delete(id);
    message.success('已删除');
    load();
  };

  const handleGenerate = async () => {
    setLoading(true);
    await careerApi.generate({ project_id: projectId });
    message.success('AI 职业体系已生成');
    await load();
    setLoading(false);
  };

  const parseLevels = (raw: string | null): any[] => {
    if (!raw) return [];
    try { return JSON.parse(raw); } catch { return []; }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><CrownOutlined style={{ marginRight: 8 }} />职业等级体系</Title>
        <Space>
          <Button icon={<PlusOutlined />}
            onClick={() => { setEditing({ name: '', description: '', levels: '[]' }); setEditOpen(true); }}>
            添加职业
          </Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={loading}>
            AI 生成
          </Button>
        </Space>
      </div>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
      {!loading && careers.length === 0 && (
        <Empty description="暂无职业体系，点击「AI 生成」根据小说类型自动创建" />
      )}

      <Row gutter={[16, 16]}>
        {careers.map((c: Career) => {
          const levels = parseLevels(c.levels);
          return (
            <Col xs={24} md={12} key={c.id}>
              <Card
                title={<Text strong>{c.name}</Text>}
                extra={
                  <Space>
                    <Button size="small" icon={<EditOutlined />}
                      onClick={() => { setEditing(c); setEditOpen(true); }} />
                    <Button size="small" danger icon={<DeleteOutlined />}
                      onClick={() => handleDelete(c.id)} />
                  </Space>
                }
              >
                {c.description && <Paragraph type="secondary" ellipsis={{ rows: 2 }}>{c.description}</Paragraph>}
                {levels.length > 0 && (
                  <Space wrap size={[4, 4]} style={{ marginTop: 8 }}>
                    {levels.map((lv: any, i: number) => (
                      <Tag key={i} color={i === levels.length - 1 ? 'gold' : 'blue'}>
                        {lv.name || lv}
                      </Tag>
                    ))}
                  </Space>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>

      <Modal title={editing?.id ? '编辑职业' : '新建职业'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={600}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input placeholder="职业名称（如：修仙者）" value={editing?.name || ''}
            onChange={(e) => setEditing((p) => ({ ...p, name: e.target.value }))} />
          <Input.TextArea placeholder="职业描述" value={editing?.description || ''}
            onChange={(e) => setEditing((p) => ({ ...p, description: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="等级 JSON [{name, description, abilities}]"
            value={editing?.levels || '[]'}
            onChange={(e) => setEditing((p) => ({ ...p, levels: e.target.value }))} rows={4} />
        </Space>
      </Modal>
    </div>
  );
}
