import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSSE } from '../../hooks/useSSE'
import { listInspirations, saveInspiration, convertToProject } from '../../api/inspiration'
import type { Inspiration } from '../../types/settings'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Badge } from '../common/Badge'
import { ProgressBar } from '../common/ProgressBar'

export default function InspirationPage() {
  const [items, setItems] = useState<Inspiration[]>([])
  const [loading, setLoading] = useState(true)
  const [prompt, setPrompt] = useState('')
  const sse = useSSE()
  const navigate = useNavigate()

  useEffect(() => {
    listInspirations().then(r => setItems(r.items)).finally(() => setLoading(false))
  }, [])

  async function handleGenerate() {
    if (!prompt.trim()) return
    await sse.startStream('/inspiration/generate-stream', { prompt, genre: '玄幻' })
  }

  async function handleSave(idea: string) {
    const res = await saveInspiration({ idea, genre_tags: '[]' })
    setItems(prev => [{ id: res.id, idea, genre_tags: null, status: 'draft', project_id: null, created_at: new Date().toISOString() }, ...prev])
  }

  async function handleConvert(id: string) {
    const res = await convertToProject(id)
    navigate(`/projects/${res.project_id}`)
  }

  if (loading) return <LoadingSpinner text="加载灵感..." />

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">灵感生成</h2>
      <div className="card mb-6">
        <h3 className="font-medium mb-3">AI 创意生成</h3>
        <div className="flex gap-2 mb-3">
          <input className="input-field flex-1" value={prompt} onChange={e => setPrompt(e.target.value)}
            placeholder="描述你想要的创意，例如：修仙世界的反派重生流..." />
          <button onClick={handleGenerate} disabled={sse.status === 'streaming' || !prompt.trim()} className="btn-primary">生成</button>
        </div>
        {sse.status !== 'idle' && (
          <div className="space-y-2">
            <ProgressBar value={sse.progress} />
            <p className="text-sm text-gray-500">{sse.message}</p>
            {sse.status === 'streaming' && sse.partialContent && (
              <div className="p-3 bg-gray-50 rounded text-sm whitespace-pre-wrap">{sse.partialContent}</div>
            )}
            {sse.status === 'completed' && sse.result && (
              <div className="p-3 bg-green-50 rounded text-sm">
                {(sse.result as Record<string, unknown>)?.ideas ? (
                  <div className="space-y-2">{((sse.result as Record<string, unknown>).ideas as string[])?.map((idea: string, i: number) => (
                    <div key={i} className="flex items-start justify-between gap-2">
                      <span>{idea}</span>
                      <button onClick={() => handleSave(idea)} className="text-xs text-primary-600 whitespace-nowrap">保存</button>
                    </div>))}
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-2">
                    <span>{JSON.stringify(sse.result)}</span>
                    <button onClick={() => handleSave(JSON.stringify(sse.result))} className="text-xs text-primary-600 whitespace-nowrap">保存</button>
                  </div>
                )}
              </div>
            )}
            {sse.status === 'error' && <p className="text-red-500 text-sm">{sse.error} <button onClick={sse.reset} className="underline">关闭</button></p>}
          </div>
        )}
      </div>

      <h3 className="font-semibold mb-3">已保存的灵感 ({items.length})</h3>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">还没有保存的灵感，生成一些创意吧</p>
      ) : (
        <div className="space-y-2">{items.map(item => (
          <div key={item.id} className="card py-3 flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm">{item.idea}</p>
              <div className="flex gap-2 mt-1">
                <Badge label={item.status} />
                {item.genre_tags && JSON.parse(item.genre_tags).map((t: string) => <Badge key={t} label={t} />)}
              </div>
            </div>
            <button onClick={() => handleConvert(item.id)} className="btn-primary btn-sm ml-4 whitespace-nowrap">转为项目</button>
          </div>
        ))}</div>
      )}
    </div>
  )
}
