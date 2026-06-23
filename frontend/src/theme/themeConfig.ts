import type { ThemeConfig } from 'antd';

export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#4D8088',
    borderRadius: 8,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      bodyBg: '#F8F6F1',
      headerBg: '#FFFFFF',
    },
    Menu: {
      itemBg: 'transparent',
    },
  },
};

export const darkThemeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#5B9BA5',
    borderRadius: 8,
    colorBgContainer: '#141414',
    colorBgElevated: '#1f1f1f',
    colorText: '#f5f5f5',
  },
};
