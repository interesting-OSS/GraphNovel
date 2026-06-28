import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { getSettings as fetchSettings } from '../api/settings';
import type { GlobalSettings } from '../types/settings';

interface SettingsContextValue {
  settings: GlobalSettings | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<GlobalSettings | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try { setSettings(await fetchSettings()); }
    catch { /* silently fail - use defaults */ }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  return (
    <SettingsContext.Provider value={{ settings, loading, refresh }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider');
  return ctx;
}
