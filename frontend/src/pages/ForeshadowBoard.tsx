import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Statistic, Modal, Input, Select, InputNumber, Empty, Spin, message, Popconfirm } from 'antd';
import { PlusOutlined, EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { foreshadowApi } from '../services/api';
import type { Foreshadow } from '../types';

const { Title, Text } = Typography;

const STATUS_OPTIONS = [
  { value: 'pending', label: '待设置', color: 'default' },
  { value: 'set', label: '已设置', color: 'blue' },
  { value: 'resolved', label: '已解决', color: 'green' },
  { value: 'abandoned', label: '已放弃', color: 'default' },
];

const CATEGORIES = ['人物伏笔', '情节伏笔', '世界观伏笔'];

export default function ForeshadowBoard() {
  const { currentProject, foreshadows, setForeshadows } = useStore();
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<Foreshadow> | null>(null);
  const projectId = currentProject?.id || '';

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data: any = await foreshadowApi.list(projectId);
      setForeshadows(data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [projectId]);

  const handleSave = async () => {
    if (!editing?.description) return;
    const data = { ...editing, project_id: projectId };
    if (editing.id) await foreshadowApi.update(editing.id, data);
    else await foreshadowApi.create(data);
    message.success('伏笔已保存');
    setEditOpen(false);
    load();
  };

  const handleDelete = async (id: string) => {
    await foreshadowApi.delete(id);
    message.success('已删除');
    load();
  };

  const stats = {
    total: foreshadows.length,
    set: foreshadows.filter((f) => f.status === 'set').length,
    resolved: foreshadows.filter((f) => f.status === 'resolved').length,
    pending: foreshadows.filter((f) => f.status === 'pending').length,
  };

  const getStatusTag = (status: string) => {
    const opt = STATUS_OPTIONS.find((s) => s.value === status);
    return <Tag color={opt?.color}>{opt?.label || status}</Tag>;
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><EyeOutlined style={{ marginRight: 8 }} />伏笔管理</Title>
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => { setEditing({ status: 'pending', category: '情节伏笔', importance: 0.5 }); setEditOpen(true); }}>
          添加伏笔
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[
          { title: '总计', value: stats.total, color: undefined },
          { title: '已设置', value: stats.set, color: '#1890ff' },
          { title: '已解决', value: stats.resolved, color: '#52c41a' },
          { title: '待设置', value: stats.pending, color: undefined },
        ].map((s) => (
          <Col xs={12} sm={6} key={s.title}>
            <Card size="small"><Statistic title={s.title} value={s.value} valueStyle={s.color ? { color: s.color } : undefined} /></Card>
          </Col>
        ))}
      </Row>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}

      {!loading && foreshadows.length === 0 && (
        <Empty description="暂无伏笔，从章节分析结果中自动识别或手动添加" />
      )}

      {foreshadows.map((item: Foreshadow) => (
        <Card key={item.id} size="small" style={{ marginBottom: 8 }}>
          <Space wrap>
            {getStatusTag(item.status)}
            <Tag>{item.category}</Tag>
            <Text>{item.description}</Text>
            {item.target_chapter_index && <Tag color="orange">目标第{item.target_chapter_index}章</Tag>}
            <Text type="secondary">重要性: {Math.round(item.importance * 100)}%</Text>
            <Button size="small" icon={<EditOutlined />}
              onClick={() => { setEditing(item); setEditOpen(true); }} />
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        </Card>
      ))}

      <Modal title={editing?.id ? '编辑伏笔' : '添加伏笔'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={500}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input.TextArea placeholder="伏笔描述" value={editing?.description || ''}
            onChange={(e) => setEditing((p) => ({ ...p, description: e.target.value }))} rows={3} />
          <Space>
            <Select value={editing?.status || 'pending'} style={{ width: 110 }}
              onChange={(v) => setEditing((p) => ({ ...p, status: v }))}
              options={STATUS_OPTIONS} />
            <Select value={editing?.category || '情节伏笔'} style={{ width: 130 }}
              onChange={(v) => setEditing((p) => ({ ...p, category: v }))}
              options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
            <InputNumber placeholder="目标章节" value={editing?.target_chapter_index}
              onChange={(v) => setEditing((p) => ({ ...p, target_chapter_index: v }))} min={1} style={{ width: 120 }} />
          </Space>
          <Text>重要性: {Math.round((editing?.importance || 0.5) * 100)}%</Text>
          <InputNumber min={0} max={1} step={0.1} value={editing?.importance || 0.5}
            onChange={(v) => setEditing((p) => ({ ...p, importance: v || 0.5 }))} style={{ width: '100%' }} />
        </Space>
      </Modal>
    </div>
  );
}
