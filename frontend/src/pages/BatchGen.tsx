import { useState, useEffect } from 'react';
import { Card, Button, InputNumber, Space, Typography, Progress, List, Tag, Empty, Spin, message, Popconfirm } from 'antd';
import { ThunderboltOutlined, StopOutlined, DeleteOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { chapterApi, taskApi } from '../services/api';
import type { BackgroundTask } from '../types';

const { Title, Text } = Typography;

export default function BatchGen() {
  const { currentProject, backgroundTasks, setBackgroundTasks } = useStore();
  const [start, setStart] = useState(1);
  const [end, setEnd] = useState(5);
  const [generating, setGenerating] = useState(false);
  const projectId = currentProject?.id || '';

  const loadTasks = async () => {
    try {
      const data: any = await taskApi.list(projectId);
      setBackgroundTasks(data.items || []);
    } catch { /* handled */ }
  };

  useEffect(() => {
    if (projectId) loadTasks();
    const timer = setInterval(() => { if (projectId) loadTasks(); }, 5000);
    return () => clearInterval(timer);
  }, [projectId]);

  const handleGenerate = async () => {
    if (start > end) { message.warning('起始章节不能大于结束章节'); return; }
    setGenerating(true);
    try {
      await chapterApi.batchGenerate(projectId, {
        start_chapter: start,
        end_chapter: end,
        generation_config: {},
      });
      message.success('批量生成任务已创建');
      loadTasks();
    } catch { /* handled */ }
    finally { setGenerating(false); }
  };

  const handleCancel = async (taskId: string) => {
    await taskApi.cancel(taskId);
    message.success('任务已取消');
    loadTasks();
  };

  const handleDelete = async (taskId: string) => {
    await taskApi.delete(taskId);
    loadTasks();
  };

  const statusColor: Record<string, string> = {
    pending: 'default', running: 'processing', paused: 'warning',
    completed: 'success', failed: 'error', cancelled: 'default',
  };

  return (
    <div>
      <Title level={4}><ThunderboltOutlined style={{ marginRight: 8 }} />批量操作</Title>

      <Card title="批量生成章节" style={{ marginBottom: 16 }}>
        <Space>
          <Text>从第</Text>
          <InputNumber min={1} value={start} onChange={(v) => setStart(v || 1)} style={{ width: 80 }} />
          <Text>章到第</Text>
          <InputNumber min={1} value={end} onChange={(v) => setEnd(v || 5)} style={{ width: 80 }} />
          <Text>章</Text>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={generating}>
            开始批量生成
          </Button>
        </Space>
      </Card>

      <Card title="后台任务">
        {backgroundTasks.length === 0 && <Empty description="暂无后台任务" />}
        {backgroundTasks.map((task: BackgroundTask) => (
          <Card key={task.id} size="small" style={{ marginBottom: 8 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Tag color={statusColor[task.status] || 'default'}>{task.status}</Tag>
                <Text>{task.task_type}</Text>
                {task.status === 'completed' && (
                  <Popconfirm title="删除此任务？" onConfirm={() => handleDelete(task.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                )}
                {task.status === 'running' && (
                  <Button size="small" danger icon={<StopOutlined />} onClick={() => handleCancel(task.id)}>取消</Button>
                )}
              </Space>
              <Progress percent={Math.round(task.progress)} size="small"
                status={task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : 'active'} />
              {task.error_message && <Text type="danger">{task.error_message}</Text>}
            </Space>
          </Card>
        ))}
      </Card>
    </div>
  );
}
