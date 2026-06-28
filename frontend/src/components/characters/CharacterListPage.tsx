import { useEffect, useState } from 'react'
import { useProject } from '../../context/ProjectContext'
import { listCharacters, createCharacter, updateCharacter, deleteCharacter } from '../../api/characters'
import type { Character } from '../../types/character'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Badge } from '../common/Badge'
import { Modal } from '../common/Modal'
import { EmptyState } from '../common/EmptyState'

export default function CharacterListPage() {
  const { project } = useProject()
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<Character | null>(null)
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    if (!project) return
    listCharacters(project.id).then(r => setCharacters(r.items)).finally(() => setLoading(false))
  }, [project])

  async function handleSave(data: Partial<Character>) {
    if (!project) return
    if (editing?.id) {
      await updateCharacter(editing.id, data)
      setCharacters(prev => prev.map(c => c.id === editing.id ? { ...c, ...data } : c))
    } else {
      const res = await createCharacter({ project_id: project.id, ...data })
      setCharacters(prev => [...prev, { ...data, id: res.id, project_id: project.id, created_at: '', updated_at: '' } as Character])
    }
    setShowForm(false); setEditing(null)
  }

  async function handleDelete(id: string) {
    if (!confirm('确定删除此角色？')) return
    await deleteCharacter(id)
    setCharacters(prev => prev.filter(c => c.id !== id))
  }

  if (loading) return <LoadingSpinner text="加载角色..." />

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">角色管理 ({characters.length})</h3>
        <button onClick={() => { setEditing(null); setShowForm(true) }} className="btn-primary btn-sm">+ 添加角色</button>
      </div>
      {characters.length === 0 ? (
        <EmptyState icon="👤" title="还没有角色" description="添加你的故事角色" action={{ label: '添加角色', onClick: () => { setEditing(null); setShowForm(true) } }} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {characters.map(c => (
            <div key={c.id} className="card group" style={{ borderLeft: `4px solid ${c.ui_color || '#4D8088'}` }}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="font-semibold">{c.name}</h4>
                  <div className="flex items-center gap-1.5 mt-1"><Badge label={c.gender} /><Badge label={c.role_type} /></div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => { setEditing(c); setShowForm(true) }} className="text-xs text-gray-400 hover:text-primary-600">✏️</button>
                  <button onClick={() => handleDelete(c.id)} className="text-xs text-gray-400 hover:text-red-500">🗑</button>
                </div>
              </div>
              {c.personality && <p className="text-sm text-gray-500 line-clamp-2">{c.personality}</p>}
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                {c.power_level && <span>⚡ {c.power_level}</span>}
                {c.current_location && <span>📍 {c.current_location}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑角色' : '新建角色'} maxWidth="max-w-2xl">
        <CharacterForm initial={editing} onSave={handleSave} onCancel={() => setShowForm(false)} />
      </Modal>
    </div>
  )
}

function CharacterForm({ initial, onSave, onCancel }: { initial: Character | null; onSave: (d: Partial<Character>) => void; onCancel: () => void }) {
  const [f, setF] = useState({
    name: initial?.name || '', gender: initial?.gender || '男', age: initial?.age || 20,
    role_type: initial?.role_type || 'supporting', appearance: initial?.appearance || '',
    personality: initial?.personality || '', background: initial?.background || '',
    goals: initial?.goals || '', secrets: initial?.secrets || '',
    mental_state: initial?.mental_state || '正常', power_level: initial?.power_level || '',
    current_location: initial?.current_location || '', motto: initial?.motto || '',
    ui_color: initial?.ui_color || '#4D8088',
  })

  return (
    <div className="grid grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto">
      <div><label className="block text-xs font-medium mb-1">姓名 *</label><input className="input-field" value={f.name} onChange={e => setF(p => ({ ...p, name: e.target.value }))} /></div>
      <div><label className="block text-xs font-medium mb-1">性别</label><select className="input-field" value={f.gender} onChange={e => setF(p => ({ ...p, gender: e.target.value }))}><option>男</option><option>女</option><option>其他</option></select></div>
      <div><label className="block text-xs font-medium mb-1">年龄</label><input type="number" className="input-field" value={f.age} onChange={e => setF(p => ({ ...p, age: +e.target.value }))} /></div>
      <div><label className="block text-xs font-medium mb-1">角色类型</label><select className="input-field" value={f.role_type} onChange={e => setF(p => ({ ...p, role_type: e.target.value }))}><option value="protagonist">主角</option><option value="supporting">配角</option><option value="antagonist">反派</option></select></div>
      <div><label className="block text-xs font-medium mb-1">战力等级</label><input className="input-field" value={f.power_level} onChange={e => setF(p => ({ ...p, power_level: e.target.value }))} /></div>
      <div><label className="block text-xs font-medium mb-1">当前位置</label><input className="input-field" value={f.current_location} onChange={e => setF(p => ({ ...p, current_location: e.target.value }))} /></div>
      <div><label className="block text-xs font-medium mb-1">心理状态</label><input className="input-field" value={f.mental_state} onChange={e => setF(p => ({ ...p, mental_state: e.target.value }))} /></div>
      <div><label className="block text-xs font-medium mb-1">UI颜色</label><input type="color" className="w-full h-9 rounded border" value={f.ui_color} onChange={e => setF(p => ({ ...p, ui_color: e.target.value }))} /></div>
      <div className="col-span-2"><label className="block text-xs font-medium mb-1">性格</label><textarea className="input-field" rows={2} value={f.personality} onChange={e => setF(p => ({ ...p, personality: e.target.value }))} /></div>
      <div className="col-span-2"><label className="block text-xs font-medium mb-1">外貌</label><textarea className="input-field" rows={2} value={f.appearance} onChange={e => setF(p => ({ ...p, appearance: e.target.value }))} /></div>
      <div className="col-span-2"><label className="block text-xs font-medium mb-1">背景</label><textarea className="input-field" rows={2} value={f.background} onChange={e => setF(p => ({ ...p, background: e.target.value }))} /></div>
      <div className="col-span-2"><label className="block text-xs font-medium mb-1">目标</label><input className="input-field" value={f.goals} onChange={e => setF(p => ({ ...p, goals: e.target.value }))} /></div>
      <div className="col-span-2"><label className="block text-xs font-medium mb-1">口头禅</label><input className="input-field" value={f.motto} onChange={e => setF(p => ({ ...p, motto: e.target.value }))} /></div>
      <div className="col-span-2 flex justify-end gap-3 pt-2">
        <button onClick={onCancel} className="btn-secondary">取消</button>
        <button onClick={() => { if (f.name.trim()) onSave(f) }} className="btn-primary" disabled={!f.name.trim()}>保存</button>
      </div>
    </div>
  )
}
