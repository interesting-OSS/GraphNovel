import { Routes, Route } from 'react-router-dom'
import { SettingsProvider } from './context/SettingsContext'
import { ProjectProvider } from './context/ProjectContext'
import AppLayout from './components/layout/AppLayout'
import Dashboard from './components/dashboard/DashboardPage'
import WizardPage from './components/wizard/WizardPage'
import WorkspacePage from './components/workspace/WorkspacePage'
import SettingsPage from './components/settings/SettingsPage'
import InspirationPage from './components/inspiration/InspirationPage'

export default function App() {
  return (
    <SettingsProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/wizard" element={<WizardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/inspiration" element={<InspirationPage />} />
          <Route path="/projects/:projectId/*" element={
            <ProjectProvider>
              <WorkspacePage />
            </ProjectProvider>
          } />
        </Route>
      </Routes>
    </SettingsProvider>
  )
}
