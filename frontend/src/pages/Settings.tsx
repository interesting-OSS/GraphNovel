import { useState, useEffect } from 'react';
import { Card, Form, Select, Input, InputNumber, Button, Typography, Space, Divider, Alert, theme, Switch, message } from 'antd';
import { ApiOutlined, RobotOutlined, SettingOutlined } from '@ant-design/icons';
import { settingsApi } from '../services/api';
import { useThemeMode } from '../theme/ThemeProvider';

const { Title, Text } = Typography;

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic Claude' },
  { value: 'gemini', label: 'Google Gemini' },
];

export default function SettingsPage() {
  const { token } = theme.useToken();
  const { mode, setMode } = useThemeMode();
  const [form] = Form.useForm();
  const [models, setModels] = useState<string[]>([]);
  const [testResult, setTestResult] = useState<{ success: boolean; preview?: string; error?: string } | null>(null);
  const [testing, setTesting] = useState(false);

  const loadModels = async (provider: string) => {
    try {
      const data: any = await settingsApi.getModels(provider);
      setModels(data.models || []);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadModels('openai');
  }, []);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const values = form.getFieldsValue();
      const result: any = await settingsApi.testConnection(values);
      setTestResult(result);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}><SettingOutlined style={{ marginRight: 8 }} /> 系统设置</Title>

      <Card title={<Space><RobotOutlined /> AI 配置</Space>} style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" initialValues={{
          ai_provider: 'openai',
          ai_model: 'gpt-4o',
          temperature: 0.7,
          max_tokens: 32000,
        }}>
          <Form.Item name="ai_provider" label="AI 提供商">
            <Select
              options={PROVIDERS}
              size="large"
              onChange={(value) => {
                form.setFieldValue('ai_model', undefined);
                loadModels(value);
              }}
            />
          </Form.Item>

          <Form.Item name="ai_model" label="模型">
            <Select options={models.map((m) => ({ value: m, label: m }))} size="large" />
          </Form.Item>

          <Form.Item name="ai_api_key" label="API Key">
            <Input.Password placeholder="输入 API Key..." size="large" />
          </Form.Item>

          <Form.Item name="ai_base_url" label="API Base URL（可选）">
            <Input placeholder="自定义 API 端点..." size="large" />
          </Form.Item>

          <Form.Item name="temperature" label="Temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: 200 }} />
          </Form.Item>

          <Form.Item name="max_tokens" label="最大 Token 数">
            <InputNumber min={1000} max={200000} step={1000} style={{ width: 200 }} />
          </Form.Item>
        </Form>

        <Button type="primary" icon={<ApiOutlined />} onClick={handleTest} loading={testing}>
          测试连接
        </Button>

        {testResult && (
          <Alert
            type={testResult.success ? 'success' : 'error'}
            message={testResult.success ? '连接成功' : '连接失败'}
            description={testResult.success ? testResult.preview : testResult.error}
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      <Card title="外观设置">
        <Space>
          <Text>主题模式：</Text>
          <Select
            value={mode}
            onChange={(value) => setMode(value as 'light' | 'dark' | 'system')}
            options={[
              { value: 'light', label: '浅色' },
              { value: 'dark', label: '深色' },
              { value: 'system', label: '跟随系统' },
            ]}
            style={{ width: 150 }}
          />
        </Space>
      </Card>
    </div>
  );
}
