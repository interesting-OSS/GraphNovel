import { useEffect, useState } from 'react'
import { useProject } from '../../context/ProjectContext'
import { listOutlines, createOutline, updateOutline, deleteOutline, reorderOutlines } from '../../api/outlines'
import type { Outline } from '../../types/outline'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Badge } from '../common/Badge'
import { EmptyState } from '../common/EmptyState'

export default function OutlineListPage() {
  const { project } = useProject()
  const [outlines, setOutlines] = useState<Outline[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!project) return
    listOutlines(project.id).then(r => setOutlines(r.items)).finally(() => setLoading(false))
  }, [project])

  async function handleAdd() {
    if (!project) return
    const idx = outlines.length + 1
    const res = await createOutline({ project_id: project.id, chapter_index: idx, title: `第${idx}章` })
    setOutlines(prev => [...prev, { id: res.id, project_id: project.id, volume: 1, chapter_index: idx, title: `第${idx}章`, summary: '', key_points: '', mode: 'one-to-one', expansion_strategy: 'balanced' }])
  }

  async function handleUpdate(o: Outline, field: string, value: string) {
    await updateOutline(o.id, { [field]: value } as Partial<Outline>)
    setOutlines(prev => prev.map(x => x.id === o.id ? { ...x, [field]: value } : x))
  }

  async function handleDelete(id: string) {
    if (!confirm('确定删除？')) return
    await deleteOutline(id)
    setOutlines(prev => prev.filter(o => o.id !== id))
  }

  async function handleMoveUp(idx: number) {
    if (idx === 0) return
    const newList = [...outlines];
    [newList[idx - 1], newList[idx]] = [newList[idx], newList[idx - 1]]
    newList.forEach((o, i) => { o.chapter_index = i + 1 })
    setOutlines(newList)
    await reorderOutlines(newList.map(o => ({ id: o.id, chapter_index: o.chapter_index })))
  }

  if (loading) return <LoadingSpinner text="加载大纲..." />

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">大纲管理 ({outlines.length})</h3>
        <button onClick={handleAdd} className="btn-primary btn-sm">+ 添加章节</button>
      </div>
      {outlines.length === 0 ? (
        <EmptyState icon="📋" title="还没有大纲" description="规划你的故事结构" action={{ label: '添加章节', onClick: handleAdd }} />
      ) : (
        <div className="space-y-2">
          {outlines.map((o, i) => (
            <div key={o.id} className="card flex items-start gap-4 py-3">
              <div className="flex flex-col items-center gap-0.5 pt-0.5">
                <button onClick={() => handleMoveUp(i)} className="text-gray-300 hover:text-gray-600 text-xs leading-none" title="上移">▲</button>
                <span className="text-sm font-bold text-gray-400 w-8 text-center">{o.chapter_index}</span>
              </div>
              <div className="flex-1 space-y-1">
                <input className="w-full text-sm font-medium border-0 focus:outline-none focus:ring-0 p-0 bg-transparent"
                       value={o.title} onChange={e => handleUpdate(o, 'title', e.target.value)} />
                <textarea className="w-full text-xs text-gray-500 border-0 focus:outline-none focus:ring-0 p-0 resize-none bg-transparent" rows={1}
                          value={o.summary || ''} onChange={e => handleUpdate(o, 'summary', e.target.value)} placeholder="章节摘要..." />
              </div>
              <div className="flex items-center gap-2 pt-0.5">
                <Badge label={o.mode} />
                <button onClick={() => handleDelete(o.id)} className="text-gray-300 hover:text-red-500 text-sm">🗑</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
