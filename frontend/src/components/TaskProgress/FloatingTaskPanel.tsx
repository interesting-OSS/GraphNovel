import { useState, useEffect } from 'react';
import { List, Progress, Tag, Button, Space, Typography, Badge, Popover, theme } from 'antd';
import {
  LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined,
  PauseCircleOutlined, DeleteOutlined, CloseOutlined,
} from '@ant-design/icons';
import { taskApi } from '../../services/api';
import type { BackgroundTask } from '../../types';

const { Text } = Typography;

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  pending: { color: 'default', icon: <LoadingOutlined /> },
  running: { color: 'blue', icon: <LoadingOutlined spin /> },
  paused: { color: 'orange', icon: <PauseCircleOutlined /> },
  completed: { color: 'green', icon: <CheckCircleOutlined /> },
  failed: { color: 'red', icon: <CloseCircleOutlined /> },
  cancelled: { color: 'default', icon: <CloseCircleOutlined /> },
};

export default function FloatingTaskPanel() {
  const { token } = theme.useToken();
  const [tasks, setTasks] = useState<BackgroundTask[]>([]);
  const [visible, setVisible] = useState(false);

  const activeTasks = tasks.filter((t) => ['pending', 'running', 'paused'].includes(t.status));
  const activeCount = activeTasks.length;

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data: any = await taskApi.list();
        const items = data.items || [];
        setTasks(items);
        if (items.some((t: BackgroundTask) => ['pending', 'running'].includes(t.status))) {
          setVisible(true);
        }
      } catch {}
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  if (activeCount === 0 && !visible) return null;

  return (
    <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 1000 }}>
      <Popover
        open={visible}
        onOpenChange={setVisible}
        trigger="click"
        placement="topRight"
        content={
          <div style={{ width: 350, maxHeight: 400, overflow: 'auto' }}>
            <List
              dataSource={tasks}
              renderItem={(task) => {
                const config = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending;
                return (
                  <List.Item
                    actions={[
                      task.can_cancel && ['pending', 'running', 'paused'].includes(task.status) && (
                        <Button size="small" key="cancel"
                          onClick={() => taskApi.cancel(task.id)}>取消</Button>
                      ),
                      ['completed', 'failed', 'cancelled'].includes(task.status) && (
                        <Button size="small" danger key="delete" icon={<DeleteOutlined />}
                          onClick={() => { taskApi.delete(task.id); setTasks((prev) => prev.filter((t) => t.id !== task.id)); }} />
                      ),
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color={config.color}>{task.status === 'running' ? '执行中' : task.status}</Tag>
                          <Text>{task.task_type}</Text>
                        </Space>
                      }
                      description={
                        <>
                          <Progress percent={Math.round(task.progress)} size="small" style={{ width: 200 }} />
                          {task.error_message && <Text type="danger">{task.error_message}</Text>}
                        </>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          </div>
        }
      >
        <Badge count={activeCount} offset={[-5, 5]}>
          <Button
            type="primary"
            shape="circle"
            size="large"
            icon={activeCount > 0 ? <LoadingOutlined spin /> : <CheckCircleOutlined />}
            style={{ boxShadow: token.boxShadowSecondary }}
          />
        </Badge>
      </Popover>
    </div>
  );
}
