import { cn } from '@/lib/utils'

interface ScoreGaugeProps {
  score: number
  label: string
  size?: number
  className?: string
}

export function ScoreGauge({ score, label, size = 120, className }: ScoreGaugeProps) {
  const radius = (size - 12) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const color = score >= 80 ? 'text-emerald-500' : score >= 50 ? 'text-amber-500' : 'text-red-500'

  return (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-muted/30"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            className={cn('transition-all duration-700 ease-out', color)}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('text-3xl font-bold', color)}>{score}</span>
          <span className="text-xs text-muted-foreground">/ 100</span>
        </div>
      </div>
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
    </div>
  )
}
