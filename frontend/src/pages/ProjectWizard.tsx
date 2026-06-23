import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Card, Form, Input, Select, InputNumber, Button, Steps, Radio, Tag, Space,
  Typography, theme, message, Row, Col, Progress, Alert
} from 'antd';
import { BookOutlined, ThunderboltOutlined, GlobalOutlined, TeamOutlined, OrderedListOutlined } from '@ant-design/icons';
import { useProjectSync } from '../store/hooks';
import { POPULAR_TAGS, CATEGORY_LIST } from './promptCategories';

const { Title, Text, Paragraph } = Typography;

const GENRES = CATEGORY_LIST;
const PERSPECTIVES = [
  { value: '第一人称', label: '第一人称' },
  { value: '第三人称', label: '第三人称' },
  { value: '第三人称有限', label: '第三人称有限视角' },
  { value: '第三人称全知', label: '第三人称全知视角' },
];

export default function ProjectWizard() {
  const navigate = useNavigate();
  const { createProject } = useProjectSync();
  const [currentStep, setCurrentStep] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [form] = Form.useForm();

  const handleCreate = async () => {
    const values = await form.validateFields();
    setGenerating(true);

    try {
      const result = await createProject(values as Record<string, unknown>);
      if (result) {
        message.success('项目创建成功！跳转到项目页面...');
        setTimeout(() => navigate(`/project/${(result as any).id}`), 1000);
      }
    } catch {
      // Error handled by hook
    } finally {
      setGenerating(false);
    }
  };

  const steps = [
    { title: '基本信息', icon: <BookOutlined /> },
    { title: '类型风格', icon: <ThunderboltOutlined /> },
    { title: '创作设定', icon: <GlobalOutlined /> },
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={3} style={{ textAlign: 'center', marginBottom: 32 }}>
        <ThunderboltOutlined style={{ marginRight: 8 }} />
        创建新小说项目
      </Title>

      <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />

      <Card>
        <Form form={form} layout="vertical" initialValues={{
          genre: '玄幻',
          narrative_perspective: '第三人称',
          target_words: 100000,
          outline_mode: 'one-to-one',
          character_count: 5,
        }}>
          <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
            <Form.Item name="title" label="书名" rules={[{ required: true, message: '请输入书名' }]}>
              <Input placeholder="给你的小说取一个名字..." size="large" />
            </Form.Item>
            <Form.Item name="description" label="一句话简介">
              <Input.TextArea rows={3} placeholder="用一句话描述你的故事..." />
            </Form.Item>
          </div>

          <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
            <Form.Item name="genre" label="小说类型">
              <Select size="large">
                {GENRES.map((g) => <Select.Option key={g} value={g}>{g}</Select.Option>)}
              </Select>
            </Form.Item>
            <Form.Item label="热门标签">
              <Space wrap>
                {POPULAR_TAGS.slice(0, 12).map((tag) => (
                  <Tag.CheckableTag key={tag} checked={false}>{tag}</Tag.CheckableTag>
                ))}
              </Space>
            </Form.Item>
          </div>

          <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
            <Form.Item name="narrative_perspective" label="叙述视角">
              <Radio.Group options={PERSPECTIVES} optionType="button" buttonStyle="solid" />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="target_words" label="目标字数">
                  <InputNumber
                    min={10000}
                    max={10000000}
                    step={10000}
                    style={{ width: '100%' }}
                    addonAfter="字"
                    size="large"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="character_count" label="预计角色数">
                  <InputNumber min={1} max={50} style={{ width: '100%' }} size="large" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="outline_mode" label="大纲模式">
              <Radio.Group optionType="button" buttonStyle="solid">
                <Radio.Button value="one-to-one">
                  <Space direction="vertical" size={0}>
                    <Text strong>传统模式 (1对1)</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>每章对应一个大纲节点</Text>
                  </Space>
                </Radio.Button>
                <Radio.Button value="one-to-many">
                  <Space direction="vertical" size={0}>
                    <Text strong>细化模式 (1对N)</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>每个大纲可展开为多章</Text>
                  </Space>
                </Radio.Button>
              </Radio.Group>
            </Form.Item>
          </div>
        </Form>

        {generating && (
          <Alert
            type="info"
            message="正在创建项目..."
            description={<Progress percent={60} status="active" />}
            style={{ marginBottom: 16 }}
          />
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
          <Button
            disabled={currentStep === 0 || generating}
            onClick={() => setCurrentStep((s) => s - 1)}
          >
            上一步
          </Button>
          {currentStep < 2 ? (
            <Button type="primary" onClick={() => setCurrentStep((s) => s + 1)}>
              下一步
            </Button>
          ) : (
            <Button type="primary" onClick={handleCreate} loading={generating} size="large">
              创建项目
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
