import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProjects, createProject, deleteProject } from '../../api/projects'
import type { ProjectSummary } from '../../types/project'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { EmptyState } from '../common/EmptyState'
import { Badge } from '../common/Badge'
import { Modal } from '../common/Modal'
import { formatWordCount, formatDate } from '../../utils/format'
import { GENRES, NARRATIVE_PERSPECTIVES } from '../../utils/constants'

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ title: '', genre: '玄幻', description: '', target_words: 100000, narrative_perspective: '第三人称' })
  const navigate = useNavigate()

  useEffect(() => {
    listProjects().then(r => setProjects(r.items)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  async function handleCreate() {
    if (!form.title.trim()) return
    const res = await createProject(form)
    setShowCreate(false)
    setForm({ title: '', genre: '玄幻', description: '', target_words: 100000, narrative_perspective: '第三人称' })
    navigate(`/projects/${res.id}`)
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm('确定删除此项目？所有数据将被清除。')) return
    await deleteProject(id)
    setProjects(prev => prev.filter(p => p.id !== id))
  }

  if (loading) return <LoadingSpinner text="加载项目列表..." />

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">我的项目</h2>
          <p className="text-sm text-gray-500 mt-1">共 {projects.length} 个项目</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">+ 新建项目</button>
      </div>

      {projects.length === 0 ? (
        <EmptyState icon="📝" title="还没有项目" description="创建你的第一个小说项目开始创作吧" action={{ label: '新建项目', onClick: () => setShowCreate(true) }} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(p => (
            <div key={p.id} onClick={() => navigate(`/projects/${p.id}`)}
                 className="card cursor-pointer hover:shadow-md transition-shadow group">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-800 group-hover:text-primary-600 transition-colors line-clamp-1">{p.title}</h3>
                <button onClick={e => handleDelete(p.id, e)} className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all text-sm">🗑</button>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <Badge label={p.genre} />
                <Badge label={p.status} />
              </div>
              {p.description && <p className="text-sm text-gray-500 line-clamp-2 mb-3">{p.description}</p>}
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{formatWordCount(p.total_word_count)}</span>
                <span>{formatDate(p.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="新建项目">
        <div className="space-y-4">
          <div><label className="block text-sm font-medium mb-1">项目标题 *</label>
            <input className="input-field" value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} placeholder="给你的小说起个名字" /></div>
          <div><label className="block text-sm font-medium mb-1">类型</label>
            <select className="input-field" value={form.genre} onChange={e => setForm(p => ({ ...p, genre: e.target.value }))}>
              {GENRES.map(g => <option key={g} value={g}>{g}</option>)}</select></div>
          <div><label className="block text-sm font-medium mb-1">简介</label>
            <textarea className="input-field" rows={3} value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder="一句话介绍你的故事" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium mb-1">目标字数</label>
              <input type="number" className="input-field" value={form.target_words} onChange={e => setForm(p => ({ ...p, target_words: +e.target.value }))} /></div>
            <div><label className="block text-sm font-medium mb-1">叙述视角</label>
              <select className="input-field" value={form.narrative_perspective} onChange={e => setForm(p => ({ ...p, narrative_perspective: e.target.value }))}>
                {NARRATIVE_PERSPECTIVES.map(n => <option key={n} value={n}>{n}</option>)}</select></div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => setShowCreate(false)} className="btn-secondary">取消</button>
            <button onClick={handleCreate} className="btn-primary" disabled={!form.title.trim()}>创建</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
