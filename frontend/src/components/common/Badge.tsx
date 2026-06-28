import { cn } from '../../utils/format'

const COLORS: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-700', polished: 'bg-blue-100 text-blue-700',
  final: 'bg-green-100 text-green-700', planning: 'bg-gray-100 text-gray-600',
  writing: 'bg-orange-100 text-orange-700', completed: 'bg-green-100 text-green-700',
  pending: 'bg-gray-100 text-gray-500', set: 'bg-purple-100 text-purple-700',
  resolved: 'bg-green-100 text-green-700', abandoned: 'bg-red-100 text-red-500',
  protagonist: 'bg-pink-100 text-pink-700', supporting: 'bg-blue-100 text-blue-700',
  antagonist: 'bg-red-100 text-red-700',
}

export function Badge({ label, className }: { label: string; className?: string }) {
  return <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', COLORS[label] || 'bg-gray-100 text-gray-600', className)}>{label}</span>
}
