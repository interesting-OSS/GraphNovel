import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSSE } from '../../hooks/useSSE'
import { createProject } from '../../api/projects'
import { ProgressBar } from '../common/ProgressBar'
import { Badge } from '../common/Badge'
import { GENRES } from '../../utils/constants'

const STEPS = [
  { id: 'init', label: '项目设定' },
  { id: 'world', label: '世界观' },
  { id: 'characters', label: '角色' },
  { id: 'careers', label: '职业' },
  { id: 'orgs', label: '组织' },
  { id: 'outline', label: '大纲' },
]

export default function WizardPage() {
  const [step, setStep] = useState(0)
  const [projectId, setProjectId] = useState<string | null>(null)
  const [form, setForm] = useState({ title: '', genre: '玄幻', description: '' })
  const [worldData, setWorldData] = useState<Record<string, unknown>>({})
  const [charData, setCharData] = useState<unknown[]>([])
  const [careerData, setCareerData] = useState<unknown[]>([])
  const [orgData, setOrgData] = useState<unknown[]>([])
  const [outlineData, setOutlineData] = useState<unknown[]>([])
  const sse = useSSE()
  const navigate = useNavigate()

  async function handleInitProject() {
    if (!form.title.trim()) return
    const res = await createProject({ ...form, target_words: 100000, narrative_perspective: '第三人称' })
    setProjectId(res.id); setStep(1)
  }

  async function handleWorldBuild() { if (projectId) await sse.startStream('/wizard-stream/world-building', { project_id: projectId, genre: form.genre, title: form.title, description: form.description }) }
  async function handleCharacters() { if (projectId) await sse.startStream('/wizard-stream/characters', { project_id: projectId, genre: form.genre, world_setting: worldData }) }
  async function handleCareers() { if (projectId) await sse.startStream('/wizard-stream/careers', { project_id: projectId, genre: form.genre, world_setting: worldData }) }
  async function handleOrgs() { if (projectId) await sse.startStream('/wizard-stream/organizations', { project_id: projectId, genre: form.genre, world_setting: worldData }) }
  async function handleOutline() { if (projectId) await sse.startStream('/wizard-stream/outline', { project_id: projectId, genre: form.genre, title: form.title, description: form.description, world_setting: worldData, characters: charData }) }

  function handleNext() {
    if (sse.result) {
      if (step === 1) setWorldData(sse.result as Record<string, unknown>)
      else if (step === 2) setCharData(((sse.result as Record<string, unknown>)?.characters as unknown[]) || [])
      else if (step === 3) setCareerData(((sse.result as Record<string, unknown>)?.careers as unknown[]) || [])
      else if (step === 4) setOrgData(((sse.result as Record<string, unknown>)?.organizations as unknown[]) || [])
      else if (step === 5) setOutlineData(((sse.result as Record<string, unknown>)?.outlines as unknown[]) || [])
      sse.reset()
    }
    if (step < STEPS.length - 1) setStep(s => s + 1)
    else navigate(`/projects/${projectId}`)
  }

  function handleRetry() {
    sse.reset()
    if (step === 1) handleWorldBuild(); else if (step === 2) handleCharacters()
    else if (step === 3) handleCareers(); else if (step === 4) handleOrgs(); else handleOutline()
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">新建项目向导</h2>
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              i < step ? 'bg-green-500 text-white' : i === step ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
              {i < step ? '✓' : i + 1}
            </div>
            <span className={`text-sm ${i === step ? 'font-medium text-gray-800' : 'text-gray-400'}`}>{s.label}</span>
            {i < STEPS.length - 1 && <div className={`w-8 h-0.5 ${i < step ? 'bg-green-400' : 'bg-gray-200'}`} />}
          </div>
        ))}
      </div>

      <div className="card min-h-[300px]">
        {step === 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">设定你的项目</h3>
            <div><label className="block text-sm font-medium mb-1">项目标题 *</label><input className="input-field" value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} placeholder="给你的小说命名" /></div>
            <div><label className="block text-sm font-medium mb-1">类型</label><select className="input-field" value={form.genre} onChange={e => setForm(p => ({ ...p, genre: e.target.value }))}>{GENRES.map(g => <option key={g} value={g}>{g}</option>)}</select></div>
            <div><label className="block text-sm font-medium mb-1">简介</label><textarea className="input-field" rows={3} value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder="简要描述你的故事" /></div>
            <button onClick={handleInitProject} className="btn-primary" disabled={!form.title.trim()}>开始创建</button>
          </div>
        )}

        {step === 1 && <WizardStepCard title="AI 生成世界观" desc="AI 将生成时代背景、地理环境、力量体系、势力和文化" onGenerate={handleWorldBuild} sse={sse}>
          {sse.status === 'completed' && sse.result && (
            <div className="mt-4 space-y-2">
              {Object.entries(sse.result).filter(([k]) => k !== 'type' && typeof sse.result![k] === 'string').map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded p-3"><span className="text-xs text-gray-400">{k}:</span> <span className="text-sm">{String(v).slice(0, 200)}</span></div>))}
            </div>)}
        </WizardStepCard>}

        {step === 2 && <WizardStepCard title="AI 生成角色" desc="AI 将创建主角、配角和反派" onGenerate={handleCharacters} sse={sse}>
          {sse.status === 'completed' && charData.length > 0 && (
            <div className="grid grid-cols-2 gap-3 mt-4">
              {charData.map((c: any, i: number) => (
                <div key={i} className="border rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1"><span className="font-medium text-sm">{c.name || '未命名'}</span><Badge label={c.role_type || 'supporting'} /></div>
                  <p className="text-xs text-gray-500 line-clamp-2">{c.personality || c.appearance || ''}</p>
                </div>))}
            </div>)}
        </WizardStepCard>}

        {step === 3 && <WizardStepCard title="AI 生成职业体系" desc="AI 将为你的世界设计职业等级体系" onGenerate={handleCareers} sse={sse}>
          {sse.status === 'completed' && careerData.length > 0 && (
            <div className="space-y-3 mt-4">{careerData.map((c: any, i: number) => (
              <div key={i} className="border rounded-lg p-3"><span className="font-medium text-sm">{c.name || '未命名职业'}</span>{c.levels && <span className="text-xs text-gray-400 ml-2">{c.levels.length} 个等级</span>}</div>))}
            </div>)}
        </WizardStepCard>}

        {step === 4 && <WizardStepCard title="AI 生成组织势力" desc="AI 将为你的世界设计门派、势力、组织体系" onGenerate={handleOrgs} sse={sse}>
          {sse.status === 'completed' && orgData.length > 0 && (
            <div className="space-y-3 mt-4">{orgData.map((o: any, i: number) => (
              <div key={i} className="border rounded-lg p-3 flex items-center gap-3">
                <span className="font-medium text-sm">{o.name || '未命名组织'}</span>
                <Badge label={o.type || o.org_type || '势力'} />
                {o.alignment && <Badge label={o.alignment} />}
                {o.goal && <span className="text-xs text-gray-400 flex-1 truncate">{String(o.goal).slice(0, 40)}</span>}
              </div>))}
            </div>)}
        </WizardStepCard>}

        {step === 5 && <WizardStepCard title="AI 生成大纲" desc="AI 将为你的故事规划章节结构" onGenerate={handleOutline} sse={sse}>
          {sse.status === 'completed' && outlineData.length > 0 && (
            <div className="mt-4 max-h-64 overflow-y-auto space-y-2">{outlineData.map((o: any, i: number) => (
              <div key={i} className="flex items-center gap-3 p-2 bg-gray-50 rounded text-sm">
                <span className="text-gray-400 w-8 text-right">{o.chapter_index || i + 1}</span>
                <span className="font-medium">{o.title || '无标题'}</span>
                {o.summary && <span className="text-gray-400 text-xs truncate flex-1">{String(o.summary).slice(0, 60)}</span>}
              </div>))}
            </div>)}
        </WizardStepCard>}

        {step > 0 && (sse.status === 'idle' || sse.status === 'completed' || sse.status === 'error') && (
          <div className="flex justify-between mt-6 pt-4 border-t border-gray-100">
            <button onClick={() => { sse.reset(); setStep(s => s - 1) }} className="btn-secondary">上一步</button>
            {sse.status === 'completed' && <button onClick={handleNext} className="btn-primary">{step === 5 ? '进入项目' : '下一步'}</button>}
            {sse.status === 'error' && <button onClick={handleRetry} className="btn-primary">重试</button>}
          </div>
        )}
      </div>
    </div>
  )
}

function WizardStepCard({ title, desc, onGenerate, sse, children }: {
  title: string; desc: string; onGenerate: () => void;
  sse: ReturnType<typeof useSSE>; children?: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-gray-500">{desc}</p>
      {sse.status === 'idle' && <button onClick={onGenerate} className="btn-primary">开始生成</button>}
      {sse.status !== 'idle' && (
        <div className="space-y-2">
          <ProgressBar value={sse.progress} />
          <p className="text-sm text-gray-500">{sse.message} ({Math.round(sse.progress)}%)</p>
          {sse.status === 'error' && <p className="text-red-500 text-sm">{sse.error}</p>}
        </div>
      )}
      {children}
    </div>
  )
}
