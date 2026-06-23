import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, theme, Switch, Space, Typography } from 'antd';
import {
  BookOutlined,
  HomeOutlined,
  SettingOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { useThemeMode } from './theme/ThemeProvider';
import ProjectList from './pages/ProjectList';
import ProjectWizard from './pages/ProjectWizard';
import ProjectDetail from './pages/ProjectDetail';
import SettingsPage from './pages/Settings';
import WorldSetting from './pages/WorldSetting';
import OutlineEditor from './pages/OutlineEditor';
import CharacterWorkshop from './pages/CharacterWorkshop';
import Chapters from './pages/Chapters';
import CareerManager from './pages/CareerManager';
import OrganizationManager from './pages/OrganizationManager';
import RelationshipMap from './pages/RelationshipMap';
import ForeshadowBoard from './pages/ForeshadowBoard';
import Inspiration from './pages/Inspiration';
import BookImport from './pages/BookImport';
import SkillManager from './pages/SkillManager';
import MCPManager from './pages/MCPManager';
import BatchGen from './pages/BatchGen';
import MemoryViewer from './pages/MemoryViewer';
import Dashboard from './pages/Dashboard';
import ChapterEditor from './pages/ChapterEditor';
import ChapterAnalysis from './pages/ChapterAnalysis';
import ChapterDiff from './pages/ChapterDiff';
import WritingStyleManager from './pages/WritingStyleManager';
import PromptTemplateManager from './pages/PromptTemplateManager';
import CoverGenerator from './pages/CoverGenerator';
import GraphMonitor from './pages/GraphMonitor';
import ReviewDashboard from './pages/ReviewDashboard';
import ChapterReader from './pages/ChapterReader';
import SkillChat from './pages/SkillChat';
import FloatingTaskPanel from './components/TaskProgress/FloatingTaskPanel';

const { Header, Content } = Layout;

function AppLayout({ children }: { children: React.ReactNode }) {
  const { token } = theme.useToken();
  const { mode, setMode } = useThemeMode();
  const location = useLocation();
  const navigate = useNavigate();

  const isDark = mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: token.colorBgContainer,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          padding: '0 24px',
        }}
      >
        <Space>
          <BookOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
          <Typography.Title level={4} style={{ margin: 0 }}>
            LangNovel Studio
          </Typography.Title>
        </Space>
        <Space>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname === '/settings' ? 'settings' : 'home']}
            style={{ border: 'none' }}
            items={[
              { key: 'home', icon: <HomeOutlined />, label: '首页' },
              { key: 'settings', icon: <SettingOutlined />, label: '设置' },
            ]}
            onClick={({ key }) => {
              if (key === 'home') navigate('/');
              if (key === 'settings') navigate('/settings');
            }}
          />
          <Switch
            checkedChildren={<BulbOutlined />}
            unCheckedChildren={<BulbOutlined />}
            checked={isDark}
            onChange={(checked) => setMode(checked ? 'dark' : 'light')}
          />
        </Space>
      </Header>
      <Content style={{ padding: '24px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
        {children}
      </Content>
      <FloatingTaskPanel />
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout><ProjectList /></AppLayout>} />
        <Route path="/projects" element={<AppLayout><ProjectList /></AppLayout>} />
        <Route path="/wizard" element={<AppLayout><ProjectWizard /></AppLayout>} />
        <Route path="/wizard/:projectId" element={<AppLayout><ProjectWizard /></AppLayout>} />
        <Route path="/settings" element={<AppLayout><SettingsPage /></AppLayout>} />
        <Route path="/inspiration" element={<AppLayout><Inspiration /></AppLayout>} />
        <Route path="/skills" element={<AppLayout><SkillManager /></AppLayout>} />
        <Route path="/mcp-plugins" element={<AppLayout><MCPManager /></AppLayout>} />
        <Route path="/book-import" element={<AppLayout><BookImport /></AppLayout>} />
        <Route path="/writing-styles" element={<AppLayout><WritingStyleManager /></AppLayout>} />
        <Route path="/prompt-templates" element={<AppLayout><PromptTemplateManager /></AppLayout>} />
        <Route path="/graph-monitor" element={<AppLayout><GraphMonitor /></AppLayout>} />
        <Route path="/skill-chat" element={<AppLayout><SkillChat /></AppLayout>} />

        {/* Project detail with nested routes */}
        <Route path="/project/:projectId" element={<ProjectDetail />}>
          <Route index element={<Chapters />} />
          <Route path="world-setting" element={<WorldSetting />} />
          <Route path="outline" element={<OutlineEditor />} />
          <Route path="careers" element={<CareerManager />} />
          <Route path="characters" element={<CharacterWorkshop />} />
          <Route path="relationships-graph" element={<RelationshipMap />} />
          <Route path="organizations" element={<OrganizationManager />} />
          <Route path="chapters" element={<Chapters />} />
          <Route path="chapter-editor" element={<ChapterEditor />} />
          <Route path="chapter-analysis" element={<ChapterAnalysis />} />
          <Route path="chapter-diff" element={<ChapterDiff />} />
          <Route path="foreshadows" element={<ForeshadowBoard />} />
          <Route path="inspiration" element={<Inspiration />} />
          <Route path="batch-gen" element={<BatchGen />} />
          <Route path="memories" element={<MemoryViewer />} />
          <Route path="book-import" element={<BookImport />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="cover-generator" element={<CoverGenerator />} />
          <Route path="graph-monitor" element={<GraphMonitor />} />
          <Route path="writing-styles" element={<WritingStyleManager />} />
          <Route path="prompt-templates" element={<PromptTemplateManager />} />
          <Route path="review" element={<ReviewDashboard />} />
          <Route path="reader" element={<ChapterReader />} />
          <Route path="skill-chat" element={<SkillChat />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
