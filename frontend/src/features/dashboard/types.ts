export type StrategyType = 'theory' | 'example' | 'simplified' | 'analogy';

export type TopicSeverity = 'WEAK' | 'DEVELOPING' | 'MASTERED';

export type CurrentLevel = 'Beginner' | 'Normal' | 'Intermediate' | 'Advanced';

export interface TeachingMethod {
  id: StrategyType;
  name: string;
  badgeLabel: string;
  tagline: string;
  description: string;
  priorityRank: number; // 1 to 4
  effectivenessPercent: number; // 0 to 100
  successfulUses: number;
  totalAttempts: number;
  color: string;
  accentBg: string;
  accentBorder: string;
  accentText: string;
  pedagogicalFocus: string;
  aiEscalationRule: string;
  keyStrengths: string[];
  sampleTrigger: string;
}

export interface WeakTopicItem {
  id: string;
  name: string;
  slug: string;
  severity: TopicSeverity;
  strategiesNeeded: number; // e.g. 3 triggers rule
  ruleExplanation: string;
  lastEncountered: string;
  subtopics: string[];
  confusionTriggers: string[];
  currentStatus: 'Requires Review' | 'In Escalation' | 'Mastered';
  suggestedAction: string;
  cycleHistory: {
    cycle: number;
    strategy: StrategyType;
    result: 'confused' | 'understood' | 'requested';
  }[];
}

export interface DashboardOverviewMetrics {
  currentLevel: CurrentLevel;
  levelSubtext: string;
  conceptsLearned: number;
  conceptsSubtext: string;
  weakTopicsCount: number;
  weakTopicsSubtext: string;
  helpfulStyle: string;
  helpfulStyleSubtext: string;
}

export interface StudentProfile {
  studentId: string;
  name: string;
  course: string;
  studyTrack: string;
  sessionDuration: string;
}
