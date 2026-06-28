export function ProgressBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.min(100, Math.max(0, value))
  return (
    <div className={`w-full bg-gray-200 rounded-full h-2 overflow-hidden ${className || ''}`}>
      <div className="bg-primary-500 h-full rounded-full transition-all duration-300" style={{ width: `${pct}%` }} />
    </div>
  )
}
