import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Typography, Space, Row, Col, message, theme } from 'antd';
import { SaveOutlined, ThunderboltOutlined, GlobalOutlined } from '@ant-design/icons';
import { ssePost } from '../utils/sseClient';
import { useStore } from '../store';
import { projectApi } from '../services/api';

const { Title, Text } = Typography;
const { TextArea } = Input;

const WORLD_DIMENSIONS = [
  { key: 'time_period', label: '时代背景', placeholder: '故事发生的时代...' },
  { key: 'geography', label: '地理版图', placeholder: '世界的地理布局...' },
  { key: 'power_system', label: '力量体系', placeholder: '修炼/魔法/科技体系...' },
  { key: 'factions', label: '势力格局', placeholder: '各方势力的分布与关系...' },
  { key: 'culture', label: '文化风俗', placeholder: '世界的文化特色和风俗习惯...' },
  { key: 'rules', label: '世界规则', placeholder: '特殊的世界规则和设定...' },
];

export default function WorldSetting() {
  const { token } = theme.useToken();
  const { currentProject } = useStore();
  const [form] = Form.useForm();
  const [generating, setGenerating] = useState(false);

  const projectId = currentProject?.id || '';

  // Load existing world setting data from store on mount
  useEffect(() => {
    if (currentProject?.world_setting) {
      try {
        const data = JSON.parse(currentProject.world_setting);
        form.setFieldsValue(data);
      } catch { /* malformed JSON, ignore */ }
    }
  }, [currentProject?.id]); // reload when project changes

  const handleSave = async () => {
    if (!projectId) {
      message.warning('项目尚未加载');
      return;
    }
    const values = form.getFieldsValue();
    try {
      await projectApi.update(projectId, { world_setting: JSON.stringify(values) });
      message.success('世界观已保存');
    } catch { message.error('保存失败'); }
  };

  const handleAIGenerate = async () => {
    setGenerating(true);
    try {
      const result = await ssePost('/api/wizard-stream/world-building', {
        project_id: currentProject?.id,
        genre: currentProject?.genre || '玄幻',
      });
      if (result && typeof result === 'object') {
        const ws = result as Record<string, unknown>;
        form.setFieldsValue(ws);
        message.success('世界观生成完成');
      }
    } catch (err) {
      message.error('生成失败');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <GlobalOutlined style={{ marginRight: 8 }} />世界观构建
        </Title>
        <Space>
          <Button icon={<SaveOutlined />} type="primary" onClick={handleSave}>保存</Button>

          <Button icon={<ThunderboltOutlined />} onClick={handleAIGenerate} loading={generating}>
            AI 生成
          </Button>
        </Space>
      </div>

      <Form form={form} layout="vertical">
        <Row gutter={[16, 0]}>
          {WORLD_DIMENSIONS.map((dim) => (
            <Col xs={24} md={12} key={dim.key}>
              <Card
                size="small"
                title={<Text strong>{dim.label}</Text>}
                style={{ marginBottom: 16, background: token.colorFillQuaternary }}
              >
                <Form.Item name={dim.key} noStyle>
                  <TextArea rows={4} placeholder={dim.placeholder} />
                </Form.Item>
              </Card>
            </Col>
          ))}
        </Row>
      </Form>
    </div>
  );
}
