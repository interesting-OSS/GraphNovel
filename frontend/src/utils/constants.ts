export const API_BASE_URL = 'http://localhost:8000/api';

export const GENRES = [
  '玄幻', '仙侠', '武侠', '言情', '科幻',
  '悬疑', '惊悚', '历史', '都市', '游戏',
  '电竞', '末世', '无限流',
] as const;

export const NARRATIVE_PERSPECTIVES = ['第一人称', '第三人称', '多视角'] as const;

export const OUTLINE_MODES = ['one-to-one', 'one-to-many'] as const;

export const CHAPTER_STATUSES = ['draft', 'polished', 'final'] as const;

export const CHARACTER_ROLE_TYPES = ['protagonist', 'supporting', 'antagonist'] as const;

export const FORESHADOW_STATUSES = ['pending', 'set', 'resolved', 'abandoned'] as const;

export const EXPANSION_STRATEGIES = ['balanced', 'climax', 'detail'] as const;

export const RELATIONSHIP_STATUSES = ['正常', '疏远', '已故', '决裂'] as const;
