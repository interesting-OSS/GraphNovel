import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Empty, Spin, message, Modal, Input } from 'antd';
import { ThunderboltOutlined, ReloadOutlined, PlusOutlined } from '@ant-design/icons';
import { skillApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

interface Skill {
  name: string;
  description?: string;
  keywords?: string[];
  file_count?: number;
}

export default function SkillManager() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newSkill, setNewSkill] = useState({ name: '', description: '' });

  const load = async () => {
    setLoading(true);
    try {
      const data: any = await skillApi.list();
      setSkills(data.skills || data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!newSkill.name) return;
    await skillApi.create({ name: newSkill.name, description: newSkill.description } as any);
    message.success('技能包已创建');
    setCreateOpen(false);
    setNewSkill({ name: '', description: '' });
    load();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><ThunderboltOutlined style={{ marginRight: 8 }} />写作技能包</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => setCreateOpen(true)}>新建技能</Button>
        </Space>
      </div>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
      {!loading && skills.length === 0 && (
        <Empty description="暂无自定义技能包" />
      )}

      <Row gutter={[16, 16]}>
        {skills.map((s) => (
          <Col xs={24} sm={12} lg={8} key={s.name}>
            <Card title={<Text strong>{s.name}</Text>} hoverable>
              {s.description && <Paragraph type="secondary" ellipsis={{ rows: 2 }}>{s.description}</Paragraph>}
              {s.keywords && (
                <Space wrap size={[4, 4]} style={{ marginTop: 8 }}>
                  {s.keywords.map((kw) => <Tag key={kw}>{kw}</Tag>)}
                </Space>
              )}
              {s.file_count !== undefined && (
                <Text type="secondary">包含 {s.file_count} 个参考文件</Text>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <Modal title="新建技能包" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={handleCreate}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input placeholder="技能名称" value={newSkill.name}
            onChange={(e) => setNewSkill((p) => ({ ...p, name: e.target.value }))} />
          <Input.TextArea placeholder="技能描述" value={newSkill.description}
            onChange={(e) => setNewSkill((p) => ({ ...p, description: e.target.value }))} rows={3} />
        </Space>
      </Modal>
    </div>
  );
}
