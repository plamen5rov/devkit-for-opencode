import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'

const STORAGE_KEY = 'devkit-session'

interface TabData {
  configContent: string
  activeTab: string
  tabResults: Record<string, any>
}

interface SessionState extends TabData {
  setConfigContent: (content: string) => void
  setActiveTab: (tab: string) => void
  setTabResult: (tab: string, result: any) => void
  clearAll: () => void
}

function loadState(): TabData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { configContent: '', activeTab: 'paste', tabResults: {} }
}

function saveState(state: TabData) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {}
}

const SessionContext = createContext<SessionState | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TabData>(loadState)

  useEffect(() => {
    saveState(state)
  }, [state])

  const setConfigContent = useCallback((content: string) => {
    setState((prev) => ({ ...prev, configContent: content }))
  }, [])

  const setActiveTab = useCallback((tab: string) => {
    setState((prev) => ({ ...prev, activeTab: tab }))
  }, [])

  const setTabResult = useCallback((tab: string, result: any) => {
    setState((prev) => ({
      ...prev,
      tabResults: { ...prev.tabResults, [tab]: result },
    }))
  }, [])

  const clearAll = useCallback(() => {
    const fresh = { configContent: '', activeTab: 'paste', tabResults: {} }
    setState(fresh)
  }, [])

  return (
    <SessionContext.Provider
      value={{ ...state, setConfigContent, setActiveTab, setTabResult, clearAll }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within SessionProvider')
  return ctx
}
