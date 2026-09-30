export type LearningLevel = 'Beginner' | 'Normal' | 'Intermediate' | 'Advanced';

export interface StudentProfile {
  id: string;
  name: string;
  role: string;
  avatarLetter: string;
  isLoggedIn: boolean;
}

export interface MetricCardData {
  title: string;
  value: string | number;
  subtext: string;
  highlightColor?: string;
  badgeText?: string;
}

export interface WeakTopicItem {
  id: string;
  name: string;
  status: 'WEAK' | 'NEEDS_PRACTICE' | 'MASTERED';
  strategiesNeeded: number;
}

export interface StrategyEffectivenessItem {
  id: string;
  strategy: 'Theory' | 'Example' | 'Simplified' | 'Analogy';
  percentage: number;
  totalAttempts?: number;
}

export interface StudentDashboardData {
  student: StudentProfile;
  currentLevel: {
    level: LearningLevel;
    subtext: string;
  };
  conceptsLearned: {
    count: number;
    subtext: string;
  };
  weakTopics: {
    count: number;
    subtext: string;
  };
  helpfulStyle: {
    style: string;
    subtext: string;
  };
  weaknessList: WeakTopicItem[];
  strategyEffectiveness: StrategyEffectivenessItem[];
}

export interface NavigationItemType {
  id: string;
  title: string;
  subtitle: string;
  path: string;
  iconName: 'layout-grid' | 'code' | 'mic' | 'check-circle-2' | 'video';
  componentBadge?: string;
}
