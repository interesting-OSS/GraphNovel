/** Flow execution monitor - shows current node status and timing. */
import { Card, Timeline, Tag, Typography, theme } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, SyncOutlined, MinusCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface FlowStep {
  node: string;
  label: string;
  status: 'completed' | 'active' | 'pending' | 'error';
  duration?: string;
}

interface FlowMonitorProps {
  steps: FlowStep[];
  currentPhase: string;
}

const statusIcons: Record<string, React.ReactNode> = {
  completed: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  active: <SyncOutlined spin style={{ color: '#1677ff' }} />,
  pending: <MinusCircleOutlined style={{ color: '#d9d9d9' }} />,
  error: <ClockCircleOutlined style={{ color: '#ff4d4f' }} />,
};

export default function FlowMonitor({ steps, currentPhase }: FlowMonitorProps) {
  const { token } = theme.useToken();

  return (
    <Card size="small" title="流程监控">
      <Timeline
        items={steps.map((step) => ({
          dot: statusIcons[step.status],
          children: (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>
                <Tag color={step.status === 'active' ? 'blue' : step.status === 'completed' ? 'green' : 'default'}>
                  {step.status === 'active' ? '执行中' : step.status === 'completed' ? '已完成' : '等待中'}
                </Tag>
                {step.label}
              </span>
              {step.duration && <Text type="secondary">{step.duration}</Text>}
            </div>
          ),
        }))}
      />
    </Card>
  );
}
