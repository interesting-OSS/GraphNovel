import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Modal, Input, Select, Empty, Spin, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import { promptTemplateApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const CATEGORIES = ['世界观', '角色', '大纲', '写作', '润色', '分析', '审稿', '灵感', '项目'];

interface PromptTemplate {
  id: string;
  name: string;
  category: string;
  content: string;
  variables?: string;
}

export default function PromptTemplateManager() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<PromptTemplate> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data: any = await promptTemplateApi.list();
      setTemplates(data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (!editing?.name) return;
    if (editing.id) await promptTemplateApi.update(editing.id, editing);
    else await promptTemplateApi.create(editing);
    message.success('提示词模板已保存');
    setEditOpen(false);
    load();
  };

  const handleDelete = async (id: string) => {
    await promptTemplateApi.delete(id);
    message.success('已删除');
    load();
  };

  const catColors: Record<string, string> = {
    '世界观': 'blue', '角色': 'green', '大纲': 'orange', '写作': 'red',
    '润色': 'purple', '分析': 'cyan', '审稿': 'magenta', '灵感': 'gold', '项目': 'geekblue',
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><FileTextOutlined style={{ marginRight: 8 }} />提示词模板</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditing({ name: '', category: '写作', content: '' }); setEditOpen(true); }}>
            新建模板
          </Button>
        </Space>
      </div>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
      {!loading && templates.length === 0 && <Empty description="暂无自定义提示词模板" />}

      <Row gutter={[16, 16]}>
        {templates.map((t: PromptTemplate) => (
          <Col xs={24} md={12} key={t.id}>
            <Card
              title={<Space><Tag color={catColors[t.category] || 'default'}>{t.category}</Tag><Text strong>{t.name}</Text></Space>}
              extra={
                <Space>
                  <Button size="small" icon={<EditOutlined />}
                    onClick={() => { setEditing(t); setEditOpen(true); }} />
                  <Popconfirm title="确定删除？" onConfirm={() => handleDelete(t.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              }
              hoverable
            >
              <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 13, background: '#fafafa', padding: 8, borderRadius: 4 }}
                ellipsis={{ rows: 4 }}>{t.content}</Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      <Modal title={editing?.id ? '编辑模板' : '新建模板'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={700}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space>
            <Input placeholder="模板名称" value={editing?.name || ''}
              onChange={(e) => setEditing((p) => ({ ...p, name: e.target.value }))} style={{ width: 200 }} />
            <Select value={editing?.category || '写作'} style={{ width: 130 }}
              onChange={(v) => setEditing((p) => ({ ...p, category: v }))}
              options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
          </Space>
          <Input placeholder="模板变量 (JSON, 可选)" value={editing?.variables || ''}
            onChange={(e) => setEditing((p) => ({ ...p, variables: e.target.value }))} />
          <Input.TextArea placeholder="模板内容..." value={editing?.content || ''}
            onChange={(e) => setEditing((p) => ({ ...p, content: e.target.value }))} rows={10} />
        </Space>
      </Modal>
    </div>
  );
}
