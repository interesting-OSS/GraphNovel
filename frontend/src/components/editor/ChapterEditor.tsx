import { useEffect, useState, useCallback } from 'react'
import { useProject } from '../../context/ProjectContext'
import { useSSE } from '../../hooks/useSSE'
import { listChapters, createChapter as apiCreateChapter, updateChapter, deleteChapter } from '../../api/chapters'
import { listOutlines } from '../../api/outlines'
import { listCharacters } from '../../api/characters'
import { listSkills, type Skill } from '../../api/skills'
import type { Chapter } from '../../types/chapter'
import type { Outline } from '../../types/outline'
import type { Character } from '../../types/character'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Badge } from '../common/Badge'
import { ProgressBar } from '../common/ProgressBar'
import { formatWordCount } from '../../utils/format'

export default function ChapterEditor() {
  const { project } = useProject()
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [outlines, setOutlines] = useState<Outline[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [activeSkill, setActiveSkill] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)
  const sse = useSSE()

  useEffect(() => {
    if (!project) return
    Promise.all([
      listChapters(project.id),
      listOutlines(project.id),
      listCharacters(project.id),
      listSkills().catch(() => ({ items: [] as Skill[] })),
    ]).then(([ch, ol, cr, sk]) => {
      setChapters(ch.items)
      setOutlines(ol.items)
      setCharacters(cr.items)
      setSkills(sk.items)
      if (ch.items.length > 0) { setActiveId(ch.items[0].id); setContent(ch.items[0].content || '') }
    }).finally(() => setLoading(false))
  }, [project])

  // Stream content into editor
  useEffect(() => {
    if (sse.status === 'streaming' && sse.partialContent) setContent(sse.partialContent)
    if (sse.status === 'completed' && sse.partialContent) { setContent(sse.partialContent); handleSave(sse.partialContent) }
  }, [sse.status, sse.partialContent])

  const handleSave = useCallback(async (text?: string) => {
    const c = text ?? content
    if (!activeId || !project) return
    await updateChapter(activeId, { content: c, word_count: c.length })
    setChapters(prev => prev.map(ch => ch.id === activeId ? { ...ch, content: c, word_count: c.length } : ch))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }, [activeId, content, project])

  function selectChapter(ch: Chapter) { setActiveId(ch.id); setContent(ch.content || ''); sse.reset() }

  async function handleAdd() {
    if (!project) return
    const maxIdx = chapters.reduce((max, c) => Math.max(max, c.chapter_index || 0), 0)
    const idx = maxIdx + 1
    const res = await apiCreateChapter({ project_id: project.id, chapter_index: idx, title: `第${idx}章`, content: '', word_count: 0 })
    const newCh: Chapter = { id: res.id, project_id: project.id, chapter_index: idx, title: `第${idx}章`, content: '', word_count: 0, status: 'draft' }
    setChapters(prev => [...prev, newCh]); selectChapter(newCh)
  }

  async function handleGenerate() {
    if (!activeId || !project) return
    const idx = chapters.find(c => c.id === activeId)?.chapter_index || 0
    await sse.startStream(`/chapters/${activeId}/generate-stream`, {
      project_id: project.id, current_chapter_index: idx, title: project.title,
      genre: project.genre, description: project.description || '',
      outlines: outlines.map(o => ({ volume: o.volume, chapter_index: o.chapter_index, title: o.title, summary: o.summary, key_points: o.key_points, mode: o.mode, expansion_strategy: o.expansion_strategy })),
      characters: characters.map(c => ({ name: c.name, role_type: c.role_type, personality: c.personality, background: c.background, goals: c.goals, power_level: c.power_level })),
      chapters: chapters.map(c => ({ chapter_index: c.chapter_index, title: c.title, content: c.content || '' })),
      world_setting: project.world_setting || {},
      generation_config: project.generation_config || {},
      writing_style_id: project.writing_style_id, active_skill: activeSkill || project.active_skill,
    })
  }

  async function handlePolish() {
    if (!activeId || !project) return
    const idx = chapters.find(c => c.id === activeId)?.chapter_index || 0
    await sse.startStream(`/chapters/${activeId}/polish`, { project_id: project.id, content, chapter_index: idx })
  }

  async function handleDelete(chId: string) {
    if (!confirm('确定删除此章节？')) return
    await deleteChapter(chId)
    setChapters(prev => prev.filter(c => c.id !== chId))
    if (activeId === chId) {
      const remaining = chapters.filter(c => c.id !== chId)
      if (remaining.length > 0) selectChapter(remaining[0])
      else { setActiveId(null); setContent('') }
    }
  }

  if (loading) return <LoadingSpinner text="加载章节..." />

  return (
    <div className="flex h-full">
      {/* Chapter list */}
      <div className="w-56 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
        <div className="p-3 border-b border-gray-100 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-600">章节列表</span>
          <button onClick={handleAdd} className="text-primary-600 text-lg leading-none hover:text-primary-800" title="添加章节">+</button>
        </div>
        {chapters.map(ch => (
          <div key={ch.id} onClick={() => selectChapter(ch)}
            className={`px-3 py-2.5 cursor-pointer border-b border-gray-50 hover:bg-gray-50 transition-colors ${
              activeId === ch.id ? 'bg-primary-50 border-l-2 border-l-primary-500' : ''}`}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium truncate">{ch.title || `第${ch.chapter_index}章`}</span>
              <button onClick={e => { e.stopPropagation(); handleDelete(ch.id) }} className="text-gray-300 hover:text-red-500 text-xs">×</button>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge label={ch.status} />
              <span className="text-xs text-gray-400">{formatWordCount(ch.word_count)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Editor */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-gray-200">
          <button onClick={handleGenerate} disabled={sse.status === 'streaming' || sse.status === 'connecting'} className="btn-primary btn-sm">🤖 AI 生成</button>
          <button onClick={handlePolish} disabled={sse.status === 'streaming' || sse.status === 'connecting' || !activeId} className="btn-secondary btn-sm">✨ 润色</button>
          <button onClick={() => handleSave()} disabled={!activeId} className="btn-secondary btn-sm">💾 保存</button>
          {saved && <span className="text-xs text-green-600 animate-pulse">✓ 已保存</span>}
          <div className="flex-1" />
          {skills.length > 0 && (
            <select value={activeSkill} onChange={e => setActiveSkill(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-600 max-w-[140px]">
              <option value="">默认风格</option>
              {skills.filter(s => s.category === 'writing').map(s => (
                <option key={s.name} value={s.name} title={s.description}>{s.display_name}</option>
              ))}
            </select>
          )}
          {activeId && <span className="text-xs text-gray-400">{formatWordCount(content.length)}</span>}
        </div>

        {sse.status !== 'idle' && (
          <div className="px-4 py-2 bg-primary-50 border-b border-primary-100 flex items-center gap-3">
            <ProgressBar value={sse.progress} className="flex-1" />
            <span className="text-xs text-primary-600 whitespace-nowrap">{Math.round(sse.progress)}% - {sse.message}</span>
            <button onClick={sse.cancel} className="text-xs text-red-500 hover:text-red-700">取消</button>
          </div>
        )}
        {sse.status === 'error' && (
          <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-sm text-red-600">
            {sse.error} <button onClick={sse.reset} className="underline ml-2">关闭</button>
          </div>
        )}

        <textarea value={content} onChange={e => setContent(e.target.value)}
          className="flex-1 w-full p-6 resize-none focus:outline-none text-base leading-relaxed font-sans"
          placeholder={activeId ? '开始创作，或点击「AI 生成」让 AI 帮你写...' : '选择一个章节开始编辑'} />
      </div>
    </div>
  )
}
