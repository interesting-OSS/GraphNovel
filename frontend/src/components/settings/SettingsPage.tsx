import { useEffect, useState } from 'react'
import { getSettings, updateSettings, testConnection, getWritingStyles } from '../../api/settings'
import type { GlobalSettings, WritingStyle } from '../../types/settings'
import { LoadingSpinner } from '../common/LoadingSpinner'

export default function SettingsPage() {
  const [settings, setSettings] = useState<GlobalSettings | null>(null)
  const [styles, setStyles] = useState<WritingStyle[]>([])
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getSettings(), getWritingStyles()])
      .then(([s, w]) => { setSettings(s); setStyles(w.items) })
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(key: string, value: string | number) {
    if (!settings) return
    await updateSettings({ [key]: value })
    setSettings(prev => prev ? { ...prev, [key]: value } : null)
  }

  async function handleTest() {
    if (!settings) return
    setTesting(true); setTestResult(null)
    try {
      const res = await testConnection({ provider: settings.ai_provider, model: settings.ai_model })
      setTestResult(res.success ? `✅ 连接成功 — ${res.preview}` : `❌ 连接失败 — ${res.error || '未知错误'}`)
    } catch (e) { setTestResult(`❌ 测试失败: ${e}`) }
    finally { setTesting(false) }
  }

  if (loading) return <LoadingSpinner text="加载设置..." />
  if (!settings) return <div className="p-6 text-red-500">加载设置失败</div>

  const PROVIDERS = [
    { value: 'openai', label: 'OpenAI' }, { value: 'deepseek', label: 'DeepSeek' },
    { value: 'anthropic', label: 'Anthropic (Claude)' }, { value: 'gemini', label: 'Google Gemini' },
    { value: 'qwen', label: '通义千问' }, { value: 'kimi', label: 'Kimi (Moonshot)' },
  ]

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">设置</h2>
      <div className="card mb-4">
        <h3 className="font-semibold mb-4">AI 提供商</h3>
        <div className="space-y-4">
          <div><label className="block text-sm font-medium mb-1">提供商</label>
            <select className="input-field" value={settings.ai_provider} onChange={e => handleSave('ai_provider', e.target.value)}>
              {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}</select></div>
          <div><label className="block text-sm font-medium mb-1">模型</label>
            <input className="input-field" value={settings.ai_model} onChange={e => handleSave('ai_model', e.target.value)} /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium mb-1">温度 ({settings.temperature})</label>
              <input type="range" min="0" max="2" step="0.1" value={settings.temperature} onChange={e => handleSave('temperature', +e.target.value)} className="w-full" /></div>
            <div><label className="block text-sm font-medium mb-1">最大 Token</label>
              <input type="number" className="input-field" value={settings.max_tokens} onChange={e => handleSave('max_tokens', +e.target.value)} /></div>
          </div>
          <button onClick={handleTest} disabled={testing} className="btn-secondary btn-sm">{testing ? '测试中...' : '🔌 测试连接'}</button>
          {testResult && <div className={`text-sm p-3 rounded ${testResult.startsWith('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>{testResult}</div>}
        </div>
      </div>
      <div className="card">
        <h3 className="font-semibold mb-4">写作风格 ({styles.length})</h3>
        {styles.length === 0 ? <p className="text-sm text-gray-400">暂无自定义风格</p> : (
          <div className="space-y-2">{styles.map(s => (
            <div key={s.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
              <span className="text-sm font-medium">{s.name}</span>
              {s.is_preset && <span className="text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">内置</span>}
              {s.content && <span className="text-xs text-gray-400 truncate flex-1">{s.content.slice(0, 80)}</span>}
            </div>))}
          </div>
        )}
      </div>
    </div>
  )
}
