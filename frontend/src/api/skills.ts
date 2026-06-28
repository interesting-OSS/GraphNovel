import { api } from './client'

export interface Skill {
  name: string
  display_name: string
  category: string
  description: string
  triggers: string[]
  content_preview: string
}

export function listSkills() {
  return api.get<{ items: Skill[] }>('/skills/list')
}
