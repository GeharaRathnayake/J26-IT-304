import { StudentDashboardData } from '../types';

export const mockDashboardData: StudentDashboardData = {
  student: {
    id: 'std_001',
    name: 'Demo',
    role: 'Student',
    avatarLetter: 'D',
    isLoggedIn: true,
  },
  currentLevel: {
    level: 'Normal',
    subtext: 'No topic in progress',
  },
  conceptsLearned: {
    count: 0,
    subtext: 'Understood in the voice tutor',
  },
  weakTopics: {
    count: 1,
    subtext: 'Needed 3 strategies to understand',
  },
  helpfulStyle: {
    style: 'Theory',
    subtext: 'Style that worked most often',
  },
  weaknessList: [
    {
      id: 'topic_1',
      name: 'Object & Class',
      status: 'WEAK',
      strategiesNeeded: 3,
    },
  ],
  strategyEffectiveness: [
    { id: 'strat_1', strategy: 'Theory', percentage: 0 },
    { id: 'strat_2', strategy: 'Example', percentage: 0 },
    { id: 'strat_3', strategy: 'Simplified', percentage: 0 },
    { id: 'strat_4', strategy: 'Analogy', percentage: 0 },
  ],
};

export const fetchStudentDashboardData = async (): Promise<StudentDashboardData> => {
  // Simulating network delay for realistic async state handling
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockDashboardData);
    }, 150);
  });
};
