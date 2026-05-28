import { NavLink, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { ThemeToggle } from './ThemeToggle'
import { useSession } from '@/lib/SessionContext'
import { Button } from './ui/button'
import {
  LayoutDashboard,
  Shield,
  Activity,
  BarChart3,
  Clock,
  GitCompare,
  Lightbulb,
  Play,
  Trash2,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/analyze', label: 'Analyze', icon: Play },
  { to: '/audit', label: 'Security', icon: Shield },
  { to: '/score', label: 'Health Score', icon: Activity },
  { to: '/history', label: 'History', icon: Clock },
  { to: '/migrate', label: 'Migration', icon: GitCompare },
  { to: '/recommendations', label: 'Recommendations', icon: Lightbulb },
]

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { clearAll } = useSession()
  const queryClient = useQueryClient()

  const handleClearAll = () => {
    clearAll()
    queryClient.clear()
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-14 items-center gap-4 px-6">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <span className="font-semibold">DevKit</span>
          </div>
          <nav className="flex items-center gap-1 ml-4">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
                    isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearAll}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="mr-1 h-4 w-4" />
              <span className="hidden sm:inline">Clear All Data</span>
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="container mx-auto px-6 py-6">
        {children}
      </main>
    </div>
  )
}
