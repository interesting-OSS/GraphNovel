import { useEffect } from 'react'
import { Routes, Route, useNavigate, useParams, useLocation } from 'react-router-dom'
import { useProject } from '../../context/ProjectContext'
import { LoadingSpinner } from '../common/LoadingSpinner'
import WorkspaceTabs from '../layout/WorkspaceTabs'
import ChapterEditor from '../editor/ChapterEditor'
import CharacterListPage from '../characters/CharacterListPage'
import OutlineListPage from '../outlines/OutlineListPage'
import WorldPage from '../world/WorldPage'

export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { project, loading, error, loadProject } = useProject()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  useEffect(() => { if (projectId) loadProject(projectId) }, [projectId, loadProject])

  useEffect(() => {
    if (pathname === `/projects/${projectId}`) navigate(`/projects/${projectId}/chapter`, { replace: true })
  }, [pathname, projectId, navigate])

  if (loading) return <LoadingSpinner text="加载项目中..." />
  if (error) return <div className="p-6 text-red-500">加载失败: {error}</div>
  if (!project) return <div className="p-6">项目未找到</div>

  return (
    <div className="flex flex-col h-full">
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
        <h2 className="text-lg font-semibold text-gray-800">{project.title}</h2>
        <span className="text-xs text-gray-400">{project.genre} | {project.status}</span>
      </div>
      <WorkspaceTabs projectId={project.id} />
      <div className="flex-1 overflow-auto">
        <Routes>
          <Route path="chapter" element={<ChapterEditor />} />
          <Route path="characters" element={<CharacterListPage />} />
          <Route path="outlines" element={<OutlineListPage />} />
          <Route path="world" element={<WorldPage />} />
        </Routes>
      </div>
    </div>
  )
}
