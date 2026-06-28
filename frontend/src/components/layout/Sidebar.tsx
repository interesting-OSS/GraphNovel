import { Link, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { path: '/', label: '项目列表', icon: '📚' },
  { path: '/wizard', label: '新建项目', icon: '✨' },
  { path: '/inspiration', label: '灵感', icon: '💡' },
  { path: '/settings', label: '设置', icon: '⚙️' },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
      <div className="p-5 border-b border-gray-100">
        <h1 className="text-lg font-bold text-primary-700">GraphNovel</h1>
        <p className="text-xs text-gray-400 mt-0.5">AI 小说创作平台</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map(item => (
          <Link key={item.path} to={item.path}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              pathname === item.path ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-600 hover:bg-gray-50'
            }`}>
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-100 text-xs text-gray-400">GraphNovel v1.0</div>
    </aside>
  )
}
