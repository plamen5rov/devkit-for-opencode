import { cn } from '@/lib/utils'

const severityConfig: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: 'bg-red-500/10', text: 'text-red-500', label: 'Critical' },
  error: { bg: 'bg-red-500/10', text: 'text-red-500', label: 'Error' },
  high: { bg: 'bg-orange-500/10', text: 'text-orange-500', label: 'High' },
  medium: { bg: 'bg-amber-500/10', text: 'text-amber-500', label: 'Medium' },
  warning: { bg: 'bg-amber-500/10', text: 'text-amber-500', label: 'Warning' },
  low: { bg: 'bg-blue-500/10', text: 'text-blue-500', label: 'Low' },
  info: { bg: 'bg-sky-500/10', text: 'text-sky-500', label: 'Info' },
  required: { bg: 'bg-red-500/10', text: 'text-red-500', label: 'Required' },
  recommended: { bg: 'bg-amber-500/10', text: 'text-amber-500', label: 'Recommended' },
  optional: { bg: 'bg-blue-500/10', text: 'text-blue-500', label: 'Optional' },
  open: { bg: 'bg-sky-500/10', text: 'text-sky-500', label: 'Open' },
  applied: { bg: 'bg-emerald-500/10', text: 'text-emerald-500', label: 'Applied' },
  dismissed: { bg: 'bg-gray-500/10', text: 'text-gray-500', label: 'Dismissed' },
}

interface SeverityBadgeProps {
  severity: string
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = severityConfig[severity.toLowerCase()] ?? {
    bg: 'bg-gray-500/10',
    text: 'text-gray-500',
    label: severity,
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.bg,
        config.text,
        className
      )}
    >
      {config.label}
    </span>
  )
}
