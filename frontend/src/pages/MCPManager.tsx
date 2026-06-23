import { useState, useEffect } from 'react';
import { Card, Button, Table, Tag, Space, Typography, Modal, Input, Select, Switch, Empty, Spin, message, Popconfirm } from 'antd';
import { PlusOutlined, ApiOutlined, ReloadOutlined, ToolOutlined } from '@ant-design/icons';
import { mcpApi } from '../services/api';
import type { MCPPlugin } from '../types';

const { Title, Text } = Typography;

export default function MCPManager() {
  const [plugins, setPlugins] = useState<MCPPlugin[]>([]);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<MCPPlugin> | null>(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [tools, setTools] = useState<any[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const data: any = await mcpApi.list();
      setPlugins(data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (!editing?.name || !editing?.url) return;
    if (editing.id) await mcpApi.update(editing.id, editing);
    else await mcpApi.create(editing);
    message.success('MCP 插件已保存');
    setEditOpen(false);
    load();
  };

  const handleToggle = async (id: string) => {
    await mcpApi.toggle(id);
    load();
  };

  const handleTest = async (id: string) => {
    const result: any = await mcpApi.test(id);
    message.info(result.healthy ? '连接正常' : `连接失败: ${result.error}`);
  };

  const handleShowTools = async (id: string) => {
    const data: any = await mcpApi.getTools(id);
    setTools(data.tools || []);
    setToolsOpen(true);
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', render: (v: string) => <Text strong>{v}</Text> },
    { title: '传输方式', dataIndex: 'transport', key: 'transport', render: (v: string) => <Tag>{v}</Tag> },
    { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
    {
      title: '状态', dataIndex: 'enabled', key: 'enabled',
      render: (v: boolean, record: MCPPlugin) => (
        <Switch checked={v} onChange={() => handleToggle(record.id)} />
      ),
    },
    {
      title: '操作', key: 'actions',
      render: (_: any, record: MCPPlugin) => (
        <Space>
          <Button size="small" icon={<ApiOutlined />} onClick={() => handleTest(record.id)}>测试</Button>
          <Button size="small" icon={<ToolOutlined />} onClick={() => handleShowTools(record.id)}>工具</Button>
          <Button size="small" onClick={() => { setEditing(record); setEditOpen(true); }}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={async () => { await mcpApi.delete(record.id); load(); }}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><ApiOutlined style={{ marginRight: 8 }} />MCP 插件管理</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditing({ transport: 'http', enabled: true, description: '' }); setEditOpen(true); }}>
            添加插件
          </Button>
        </Space>
      </div>

      <Table columns={columns} dataSource={plugins} rowKey="id" loading={loading}
        locale={{ emptyText: <Empty description="暂无 MCP 插件，添加外部工具扩展 AI 能力" /> }}
        pagination={false} />

      <Modal title={editing?.id ? '编辑插件' : '添加 MCP 插件'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={500}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input placeholder="插件名称" value={editing?.name || ''}
            onChange={(e) => setEditing((p) => ({ ...p, name: e.target.value }))} />
          <Input.TextArea placeholder="插件描述（可选）" value={editing?.description || ''} rows={3}
            onChange={(e) => setEditing((p) => ({ ...p, description: e.target.value }))} />
          <Select value={editing?.transport || 'http'} style={{ width: '100%' }}
            onChange={(v) => setEditing((p) => ({ ...p, transport: v }))}
            options={[
              { value: 'http', label: 'HTTP' },
              { value: 'streamable_http', label: 'Streamable HTTP' },
              { value: 'sse', label: 'SSE' },
            ]} />
          <Input placeholder="服务器 URL" value={editing?.url || ''}
            onChange={(e) => setEditing((p) => ({ ...p, url: e.target.value }))} />
        </Space>
      </Modal>

      <Modal title="可用工具" open={toolsOpen} onCancel={() => setToolsOpen(false)} footer={null} width={600}>
        {tools.length === 0 ? <Empty description="该插件未提供工具" /> : (
          tools.map((t: any, i: number) => (
            <Card key={i} size="small" style={{ marginBottom: 8 }}>
              <Text strong>{t.name}</Text>
              {t.description && <Typography.Paragraph type="secondary">{t.description}</Typography.Paragraph>}
            </Card>
          ))
        )}
      </Modal>
    </div>
  );
}
