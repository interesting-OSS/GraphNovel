import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ConfigProvider, theme as antTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { themeConfig, darkThemeConfig } from './themeConfig';

type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  mode: ThemeMode;
  resolvedMode: 'light' | 'dark';
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: 'system',
  resolvedMode: 'light',
  setMode: () => {},
});

export const useThemeMode = () => useContext(ThemeContext);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('theme-mode');
    return (saved as ThemeMode) || 'system';
  });

  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches,
  );

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const resolvedMode = mode === 'system' ? (systemDark ? 'dark' : 'light') : mode;

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
    localStorage.setItem('theme-mode', newMode);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme-mode', mode);
    document.documentElement.setAttribute('data-theme-resolved', resolvedMode);
    document.documentElement.style.colorScheme = resolvedMode;
  }, [mode, resolvedMode]);

  const config = resolvedMode === 'dark' ? darkThemeConfig : themeConfig;

  return (
    <ThemeContext.Provider value={{ mode, resolvedMode, setMode }}>
      <ConfigProvider
        theme={{
          ...config,
          algorithm: resolvedMode === 'dark' ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        }}
        locale={zhCN}
      >
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
};
