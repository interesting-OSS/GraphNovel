import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Modal, Input, Select, Empty, Spin, message } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { organizationApi } from '../services/api';
import type { Organization } from '../types';

const { Title, Text, Paragraph } = Typography;

const ORG_TYPES = ['门派', '家族', '商会', '势力', '国家', '组织'];

export default function OrganizationManager() {
  const { currentProject, organizations, setOrganizations } = useStore();
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<Organization> | null>(null);
  const projectId = currentProject?.id || '';

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data: any = await organizationApi.list(projectId);
      setOrganizations(data.items || []);
    } catch { /* interceptor handles */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [projectId]);

  const handleSave = async () => {
    if (!editing?.name) return;
    const data = { ...editing, project_id: projectId };
    if (editing.id) await organizationApi.update(editing.id, data);
    else await organizationApi.create(data);
    message.success('组织已保存');
    setEditOpen(false);
    load();
  };

  const handleDelete = async (id: string) => {
    await organizationApi.delete(id);
    message.success('已删除');
    load();
  };

  const handleGenerate = async () => {
    setLoading(true);
    await organizationApi.generate({ project_id: projectId });
    message.success('AI 组织生成中');
    await load();
    setLoading(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><TeamOutlined style={{ marginRight: 8 }} />组织势力</Title>
        <Space>
          <Button icon={<PlusOutlined />}
            onClick={() => { setEditing({ name: '', org_type: '门派' }); setEditOpen(true); }}>
            添加组织
          </Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={loading}>
            AI 生成
          </Button>
        </Space>
      </div>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
      {!loading && organizations.length === 0 && (
        <Empty description="暂无组织，点击「AI 生成」自动创建门派势力" />
      )}

      <Row gutter={[16, 16]}>
        {organizations.map((org: Organization) => (
          <Col xs={24} sm={12} lg={8} key={org.id}>
            <Card
              title={<Space><Tag color="blue">{org.org_type}</Tag><Text strong>{org.name}</Text></Space>}
              extra={
                <Space>
                  <Button size="small" icon={<EditOutlined />}
                    onClick={() => { setEditing(org); setEditOpen(true); }} />
                  <Button size="small" danger icon={<DeleteOutlined />}
                    onClick={() => handleDelete(org.id)} />
                </Space>
              }
            >
              {org.description && <Paragraph type="secondary" ellipsis={{ rows: 2 }}>{org.description}</Paragraph>}
              {org.goal && <Text type="secondary">目标：{org.goal}</Text>}
            </Card>
          </Col>
        ))}
      </Row>

      <Modal title={editing?.id ? '编辑组织' : '新建组织'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={600}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space>
            <Input placeholder="组织名称" value={editing?.name || ''}
              onChange={(e) => setEditing((p) => ({ ...p, name: e.target.value }))} style={{ width: 200 }} />
            <Select placeholder="类型" value={editing?.org_type || '门派'}
              onChange={(v) => setEditing((p) => ({ ...p, org_type: v }))} style={{ width: 120 }}
              options={ORG_TYPES.map((t) => ({ value: t, label: t }))} />
          </Space>
          <Input.TextArea placeholder="组织描述" value={editing?.description || ''}
            onChange={(e) => setEditing((p) => ({ ...p, description: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="组织目标" value={editing?.goal || ''}
            onChange={(e) => setEditing((p) => ({ ...p, goal: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="层级结构 JSON（可选）" value={editing?.hierarchy || ''}
            onChange={(e) => setEditing((p) => ({ ...p, hierarchy: e.target.value }))} rows={3} />
        </Space>
      </Modal>
    </div>
  );
}
