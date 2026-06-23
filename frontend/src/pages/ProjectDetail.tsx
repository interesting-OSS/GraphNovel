import { useEffect, useState } from 'react';
import { useParams, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Spin, Typography, Button, Space, theme } from 'antd';
import {
  GlobalOutlined, OrderedListOutlined, TeamOutlined, ReadOutlined,
  BarChartOutlined, EyeOutlined, SettingOutlined,
  ApartmentOutlined, NodeIndexOutlined, BulbOutlined, ArrowLeftOutlined,
  ThunderboltOutlined, DatabaseOutlined, FileTextOutlined, HomeOutlined,
  EditOutlined, HistoryOutlined, PictureOutlined,
  FormatPainterOutlined, ApiOutlined, AuditOutlined, MessageOutlined,
} from '@ant-design/icons';
import { useStore } from '../store';
import { projectApi } from '../services/api';

const { Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: 'dashboard', icon: <HomeOutlined />, label: '项目概览' },
  { key: 'world-setting', icon: <GlobalOutlined />, label: '世界观' },
  { key: 'outline', icon: <OrderedListOutlined />, label: '大纲' },
  { key: 'careers', icon: <ApartmentOutlined />, label: '职业体系' },
  { key: 'characters', icon: <TeamOutlined />, label: '角色工坊' },
  { key: 'relationships-graph', icon: <NodeIndexOutlined />, label: '关系图谱' },
  { key: 'organizations', icon: <ApartmentOutlined />, label: '组织势力' },
  { key: 'chapters', icon: <ReadOutlined />, label: '章节写作' },
  { key: 'chapter-editor', icon: <EditOutlined />, label: '章节编辑器' },
  { key: 'chapter-analysis', icon: <BarChartOutlined />, label: '章节分析' },
  { key: 'chapter-diff', icon: <HistoryOutlined />, label: '版本对比' },
  { key: 'batch-gen', icon: <ThunderboltOutlined />, label: '批量操作' },
  { key: 'foreshadows', icon: <EyeOutlined />, label: '伏笔管理' },
  { key: 'memories', icon: <DatabaseOutlined />, label: '记忆检索' },
  { key: 'book-import', icon: <FileTextOutlined />, label: '拆书导入' },
  { key: 'cover-generator', icon: <PictureOutlined />, label: '封面生成' },
  { key: 'inspiration', icon: <BulbOutlined />, label: '灵感' },
  { key: 'writing-styles', icon: <FormatPainterOutlined />, label: '写作风格' },
  { key: 'prompt-templates', icon: <FileTextOutlined />, label: '提示词模板' },
  { key: 'review', icon: <AuditOutlined />, label: '智能审稿' },
  { key: 'reader', icon: <ReadOutlined />, label: '阅读模式' },
  { key: 'graph-monitor', icon: <ApiOutlined />, label: '图流程监控' },
  { key: 'skill-chat', icon: <MessageOutlined />, label: '技能对话' },
  { key: 'settings', icon: <SettingOutlined />, label: '项目设置' },
];

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const { currentProject, setCurrentProject, loading, setLoading } = useStore();
  const [collapsed, setCollapsed] = useState(false);

  const currentTab = (() => {
    const segments = location.pathname.split('/');
    const last = segments[segments.length - 1];
    // If the last segment is the project ID itself, default to 'chapters'
    const validTabs = menuItems.map((m) => m.key);
    return validTabs.includes(last) ? last : 'chapters';
  })();

  useEffect(() => {
    if (projectId) {
      setLoading(true);
      projectApi.get(projectId)
        .then((data: any) => setCurrentProject(data))
        .catch(() => navigate('/'))
        .finally(() => setLoading(false));
    }
  }, [projectId]);

  if (loading || !currentProject) {
    return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;
  }

  return (
    <Layout style={{ minHeight: '100vh', background: token.colorBgLayout }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={220}
        style={{ background: token.colorBgContainer }}
      >
        <div style={{ padding: '16px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/')}
            style={{ marginBottom: 8 }}
          >
            返回
          </Button>
          <Title level={5} style={{ margin: 0 }} ellipsis={{ tooltip: currentProject.title }}>
            {currentProject.title}
          </Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[currentTab]}
          items={menuItems}
          onClick={({ key }) => navigate(`/project/${projectId}/${key}`)}
        />
      </Sider>
      <Content style={{ padding: 24, overflow: 'auto' }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
