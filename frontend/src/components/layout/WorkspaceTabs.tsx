import { NavLink } from 'react-router-dom'

const TABS = [
  { path: 'chapter', label: '章节编辑', icon: '✍️' },
  { path: 'characters', label: '角色', icon: '👤' },
  { path: 'outlines', label: '大纲', icon: '📋' },
  { path: 'world', label: '世界观', icon: '🌍' },
]

export default function WorkspaceTabs({ projectId }: { projectId: string }) {
  const base = `/projects/${projectId}`
  return (
    <div className="flex border-b border-gray-200 bg-white px-6">
      {TABS.map(tab => (
        <NavLink key={tab.path} to={`${base}/${tab.path}`}
          className={({ isActive }) => `flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors ${
            isActive ? 'border-primary-600 text-primary-700 font-medium' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}>
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </NavLink>
      ))}
    </div>
  )
}
