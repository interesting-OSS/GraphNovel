import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Modal, Input, Empty, Spin, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FormatPainterOutlined, ReloadOutlined } from '@ant-design/icons';
import { writingStyleApi } from '../services/api';
import type { WritingStyle } from '../types';

const { Title, Text, Paragraph } = Typography;

export default function WritingStyleManager() {
  const [styles, setStyles] = useState<WritingStyle[]>([]);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<WritingStyle> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data: any = await writingStyleApi.list();
      setStyles(data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (!editing?.name) return;
    if (editing.id) await writingStyleApi.update(editing.id, editing);
    else await writingStyleApi.create(editing);
    message.success('写作风格已保存');
    setEditOpen(false);
    load();
  };

  const handleDelete = async (id: string) => {
    await writingStyleApi.delete(id);
    message.success('已删除');
    load();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><FormatPainterOutlined style={{ marginRight: 8 }} />写作风格</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditing({ name: '', description: '', content: '', is_preset: false }); setEditOpen(true); }}>
            新建风格
          </Button>
        </Space>
      </div>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}

      <Row gutter={[16, 16]}>
        {styles.map((s: WritingStyle) => (
          <Col xs={24} sm={12} lg={8} key={s.id}>
            <Card
              title={<Space>{s.is_preset && <Tag color="gold">预置</Tag>}<Text strong>{s.name}</Text></Space>}
              extra={
                <Space>
                  <Button size="small" icon={<EditOutlined />}
                    onClick={() => { setEditing(s); setEditOpen(true); }} />
                  {!s.is_preset && (
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(s.id)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  )}
                </Space>
              }
              hoverable
            >
              {s.description && <Paragraph type="secondary" ellipsis={{ rows: 2 }}>{s.description}</Paragraph>}
              {s.content && (
                <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 13, background: '#fafafa', padding: 8, borderRadius: 4 }}
                  ellipsis={{ rows: 3 }}>{s.content}</Paragraph>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <Modal title={editing?.id ? '编辑风格' : '新建写作风格'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={600}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input placeholder="风格名称（如：古风、轻小说）" value={editing?.name || ''}
            onChange={(e) => setEditing((p) => ({ ...p, name: e.target.value }))} />
          <Input.TextArea placeholder="风格描述" value={editing?.description || ''}
            onChange={(e) => setEditing((p) => ({ ...p, description: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="风格内容（系统提示词）" value={editing?.content || ''}
            onChange={(e) => setEditing((p) => ({ ...p, content: e.target.value }))} rows={6} />
        </Space>
      </Modal>
    </div>
  );
}
