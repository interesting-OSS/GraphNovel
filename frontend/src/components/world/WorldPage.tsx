import { useEffect, useState } from 'react'
import { useProject } from '../../context/ProjectContext'
import { listOrganizations, createOrganization, deleteOrganization } from '../../api/organizations'
import { listCareers, createCareer, deleteCareer } from '../../api/careers'
import { listRelationships, createRelationship, deleteRelationship } from '../../api/relationships'
import { listForeshadows, createForeshadow, deleteForeshadow, plantForeshadow, resolveForeshadow, getForeshadowStats } from '../../api/foreshadows'
import type { Organization, Career, CharacterRelationship } from '../../types/organization'
import type { Foreshadow, ForeshadowStatistics } from '../../types/foreshadow'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Badge } from '../common/Badge'
import { EmptyState } from '../common/EmptyState'

type TabId = 'world' | 'orgs' | 'careers' | 'relationships' | 'foreshadows'

export default function WorldPage() {
  const { project } = useProject()
  const [tab, setTab] = useState<TabId>('world')
  const [orgs, setOrgs] = useState<Organization[]>([])
  const [careers, setCareers] = useState<Career[]>([])
  const [rels, setRels] = useState<CharacterRelationship[]>([])
  const [fores, setFores] = useState<Foreshadow[]>([])
  const [stats, setStats] = useState<ForeshadowStatistics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!project) return
    Promise.allSettled([
      listOrganizations(project.id), listCareers(project.id),
      listRelationships(project.id), listForeshadows(project.id),
      getForeshadowStats(project.id),
    ]).then((results) => {
      const [o, c, r, f, s] = results
      if (o.status === 'fulfilled') setOrgs(o.value.items)
      if (c.status === 'fulfilled') setCareers(c.value.items)
      if (r.status === 'fulfilled') setRels(r.value.items)
      if (f.status === 'fulfilled') setFores(f.value.items)
      if (s.status === 'fulfilled') setStats(s.value.statistics)
      setLoading(false)
    })
  }, [project])

  if (loading) return <LoadingSpinner text="加载世界观数据..." />

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'world', label: '世界观设定', icon: '🌍' },
    { id: 'orgs', label: `组织 (${orgs.length})`, icon: '🏛' },
    { id: 'careers', label: `职业 (${careers.length})`, icon: '⚔️' },
    { id: 'foreshadows', label: `伏笔 (${fores.length})`, icon: '🔮' },
    { id: 'relationships', label: `关系 (${rels.length})`, icon: '🔗' },
  ]

  return (
    <div className="p-6">
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${tab === t.id ? 'bg-white shadow-sm font-medium text-gray-800' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'world' && (
        <div className="card">
          <h4 className="font-semibold mb-4">世界观设定</h4>
          {project?.world_setting && typeof project.world_setting === 'object' && Object.keys(project.world_setting as Record<string, unknown>).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(project.world_setting as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="border rounded-lg p-3">
                  <div className="text-xs text-gray-400 mb-1">{k}</div>
                  <div className="text-sm whitespace-pre-wrap">{typeof v === 'string' ? String(v).slice(0, 500) : JSON.stringify(v, null, 2).slice(0, 500)}</div>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="🌍" title="尚未生成世界观" description="通过项目向导生成世界观设定" />}
        </div>
      )}

      {tab === 'orgs' && (
        <div>
          <button onClick={async () => {
            if (!project) return
            const res = await createOrganization({ project_id: project.id, name: '新组织', org_type: '门派' })
            setOrgs(prev => [...prev, { id: res.id, project_id: project.id, name: '新组织', org_type: '门派', leader_id: null, goal: '', description: '', hierarchy: null, alignment: '中立', created_at: '', updated_at: '' }])
          }} className="btn-primary btn-sm mb-3">+ 添加组织</button>
          {orgs.length === 0 ? <EmptyState icon="🏛" title="还没有组织" /> : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {orgs.map(o => (
                <div key={o.id} className="card py-3 flex items-center justify-between">
                  <div><span className="font-medium text-sm">{o.name}</span>
                    <div className="flex gap-1 mt-1"><Badge label={o.org_type} /><Badge label={o.alignment} /></div></div>
                  <button onClick={async () => { await deleteOrganization(o.id); setOrgs(prev => prev.filter(x => x.id !== o.id)) }} className="text-gray-300 hover:text-red-500">🗑</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'careers' && (
        <div>
          <button onClick={async () => {
            if (!project) return
            const res = await createCareer({ project_id: project.id, name: '新职业', career_type: '主要职业' })
            setCareers(prev => [...prev, { id: res.id, project_id: project.id, name: '新职业', career_type: '主要职业', description: '', levels: null }])
          }} className="btn-primary btn-sm mb-3">+ 添加职业</button>
          {careers.length === 0 ? <EmptyState icon="⚔️" title="还没有职业体系" /> : (
            <div className="space-y-2">{careers.map(c => (
              <div key={c.id} className="card py-3 flex items-center justify-between">
                <div><span className="font-medium text-sm">{c.name}</span>
                  <span className="text-xs text-gray-400 ml-2">{c.career_type}</span>
                  {c.levels && <span className="text-xs text-gray-400 ml-2">• {c.levels.length} 个等级</span>}</div>
                <button onClick={async () => { await deleteCareer(c.id); setCareers(prev => prev.filter(x => x.id !== c.id)) }} className="text-gray-300 hover:text-red-500">🗑</button>
              </div>
            ))}</div>
          )}
        </div>
      )}

      {tab === 'foreshadows' && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>总计 {fores.length}</span>
              {stats && <span>解决率 {stats.resolution_rate}%</span>}
            </div>
            <button onClick={async () => {
              if (!project) return
              const res = await createForeshadow({ project_id: project.id, description: '新伏笔', category: '情节伏笔', importance: 5 })
              setFores(prev => [...prev, { id: res.id, project_id: project.id, description: '新伏笔', status: 'pending', category: '情节伏笔', set_chapter_id: null, target_chapter_index: null, resolved_chapter_id: null, remind_deadline: null, importance: 5, created_at: '', updated_at: '' }])
            }} className="btn-primary btn-sm">+ 添加伏笔</button>
          </div>
          {fores.length === 0 ? <EmptyState icon="🔮" title="还没有伏笔" /> : (
            <div className="space-y-2">{fores.map(f => (
              <div key={f.id} className="card py-3 flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1"><Badge label={f.status} /><Badge label={f.category} /><span className="text-xs text-gray-400">重要性: {f.importance}/10</span></div>
                  <p className="text-sm">{f.description}</p>
                </div>
                <div className="flex gap-1 ml-3">
                  {f.status === 'pending' && <button onClick={async () => { await plantForeshadow(f.id); setFores(prev => prev.map(x => x.id === f.id ? { ...x, status: 'set' } : x)) }} className="text-xs text-purple-600 hover:text-purple-800">布置</button>}
                  {f.status === 'set' && <button onClick={async () => { await resolveForeshadow(f.id); setFores(prev => prev.map(x => x.id === f.id ? { ...x, status: 'resolved' } : x)) }} className="text-xs text-green-600 hover:text-green-800">解决</button>}
                  <button onClick={async () => { await deleteForeshadow(f.id); setFores(prev => prev.filter(x => x.id !== f.id)) }} className="text-xs text-gray-300 hover:text-red-500 ml-1">🗑</button>
                </div>
              </div>
            ))}</div>
          )}
        </div>
      )}

      {tab === 'relationships' && (
        <div>
          <button onClick={async () => {
            if (!project) return
            const res = await createRelationship({ project_id: project.id, char_a_id: '', char_b_id: '', relation_type: '其他' })
            setRels(prev => [...prev, { id: res.id, project_id: project.id, char_a_id: '', char_b_id: '', relation_type: '其他', description: '', intimacy: 50, status: '正常', source: 'manual', created_at: '', updated_at: '' }])
          }} className="btn-primary btn-sm mb-3">+ 添加关系</button>
          {rels.length === 0 ? <EmptyState icon="🔗" title="还没有角色关系" /> : (
            <div className="space-y-2">{rels.map(r => (
              <div key={r.id} className="card py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{r.char_a_id || '?'} ↔ {r.char_b_id || '?'}</span>
                  <Badge label={r.relation_type} />
                  <div className="w-20 bg-gray-200 rounded-full h-1.5"><div className="bg-pink-400 h-1.5 rounded-full" style={{ width: `${r.intimacy}%` }} /></div>
                </div>
                <button onClick={async () => { await deleteRelationship(r.id); setRels(prev => prev.filter(x => x.id !== r.id)) }} className="text-gray-300 hover:text-red-500">🗑</button>
              </div>
            ))}</div>
          )}
        </div>
      )}
    </div>
  )
}
