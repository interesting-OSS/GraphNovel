import { useState } from 'react';
import { Card, Button, Input, List, Space, Typography, message } from 'antd';
import { BulbOutlined, ThunderboltOutlined, SaveOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { ssePost } from '../utils/sseClient';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

export default function Inspiration() {
  const [ideas, setIdeas] = useState<string[]>([]);
  const [generating, setGenerating] = useState(false);
  const [input, setInput] = useState('');

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await ssePost('/api/inspiration/generate-stream', {
        genre: input || '玄幻',
      });
      if (result?.content) {
        setIdeas((prev) => [result.content as string, ...prev]);
      }
    } catch {
      message.error('灵感生成失败');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <Title level={4}>
        <BulbOutlined style={{ marginRight: 8 }} />灵感模式
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <TextArea
            rows={3}
            placeholder="描述你想要的灵感方向...（例如：一个废柴主角意外获得远古传承的故事）"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={generating}>
            生成灵感
          </Button>
        </Space>
      </Card>

      <List
        dataSource={ideas}
        locale={{ emptyText: '暂无灵感，输入方向并点击生成' }}
        renderItem={(idea: string, index: number) => (
          <Card
            size="small"
            style={{ marginBottom: 8 }}
            actions={[
              <SaveOutlined key="save" onClick={() => message.success('灵感已保存')} />,
              <ArrowRightOutlined key="convert" onClick={() => message.info('已转为项目')} />,
            ]}
          >
            <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{idea}</Paragraph>
          </Card>
        )}
      />
    </div>
  );
}
