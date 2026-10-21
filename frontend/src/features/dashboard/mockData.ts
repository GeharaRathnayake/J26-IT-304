import type {
  DashboardOverviewMetrics,
  StudentProfile,
  TeachingMethod,
  WeakTopicItem,
} from './types';

export const INITIAL_METRICS: DashboardOverviewMetrics = {
  currentLevel: 'Normal',
  levelSubtext: 'No topic in progress',
  conceptsLearned: 0,
  conceptsSubtext: 'Understood in the voice tutor',
  weakTopicsCount: 1,
  weakTopicsSubtext: 'Needed 3 strategies to understand',
  helpfulStyle: 'Theory',
  helpfulStyleSubtext: 'Style that worked most often',
};

export const INITIAL_WEAK_TOPICS: WeakTopicItem[] = [
  {
    id: 'classes_and_objects',
    name: 'Object & Class',
    slug: 'classes_and_objects',
    severity: 'WEAK',
    strategiesNeeded: 3,
    ruleExplanation:
      'A topic is stored here as WEAK when the student needed 3 strategies to understand that one question.',
    lastEncountered: 'Just now',
    subtopics: [
      'Class definition vs Instance instantiation',
      'Memory allocation in Heap vs Stack',
      'Default and Parameterized Constructors',
    ],
    confusionTriggers: [
      'Distinguishing reference variables from object instances',
      'The "new" keyword memory model',
    ],
    currentStatus: 'Requires Review',
    suggestedAction: 'Practice with Analogy or step-by-step code example in tutor',
    cycleHistory: [
      { cycle: 1, strategy: 'theory', result: 'confused' },
      { cycle: 2, strategy: 'example', result: 'confused' },
      { cycle: 3, strategy: 'simplified', result: 'confused' },
    ],
  },
];

export const POPULATED_WEAK_TOPICS: WeakTopicItem[] = [
  {
    id: 'classes_and_objects',
    name: 'Object & Class',
    slug: 'classes_and_objects',
    severity: 'WEAK',
    strategiesNeeded: 3,
    ruleExplanation:
      'A topic is stored here as WEAK when the student needed 3 strategies to understand that one question.',
    lastEncountered: 'Today, 2:15 PM',
    subtopics: ['Constructors', 'Instantiation', 'Reference Variables'],
    confusionTriggers: ['Heap vs Stack reference ambiguity', 'Object state mutability'],
    currentStatus: 'Requires Review',
    suggestedAction: 'Review blueprint analogy and run live constructor trace in tutor',
    cycleHistory: [
      { cycle: 1, strategy: 'theory', result: 'confused' },
      { cycle: 2, strategy: 'example', result: 'confused' },
      { cycle: 3, strategy: 'simplified', result: 'confused' },
    ],
  },
  {
    id: 'recursion',
    name: 'Recursion & Call Stack',
    slug: 'recursion',
    severity: 'WEAK',
    strategiesNeeded: 3,
    ruleExplanation:
      'Needed 3 strategies (Theory -> Simplified -> Analogy) before resolving base case condition.',
    lastEncountered: 'Yesterday',
    subtopics: ['Base Cases', 'Stack Overflow', 'Recursive Unwinding'],
    confusionTriggers: ['Infinite recursion recursion depth', 'Return stack unwinding'],
    currentStatus: 'In Escalation',
    suggestedAction: 'Trace recursive tree calls with visual step walkthrough',
    cycleHistory: [
      { cycle: 1, strategy: 'theory', result: 'confused' },
      { cycle: 2, strategy: 'example', result: 'confused' },
      { cycle: 3, strategy: 'analogy', result: 'understood' },
    ],
  },
  {
    id: 'polymorphism',
    name: 'Polymorphism & Dynamic Binding',
    slug: 'polymorphism',
    severity: 'DEVELOPING',
    strategiesNeeded: 2,
    ruleExplanation: 'Resolved in 2 strategies; borderline threshold.',
    lastEncountered: '2 days ago',
    subtopics: ['Method Overriding', 'Virtual Method Table', 'Upcasting'],
    confusionTriggers: ['Compile-time vs Runtime resolution'],
    currentStatus: 'Requires Review',
    suggestedAction: 'Quick self-check question in tutor',
    cycleHistory: [
      { cycle: 1, strategy: 'theory', result: 'confused' },
      { cycle: 2, strategy: 'example', result: 'understood' },
    ],
  },
];

export const INITIAL_TEACHING_METHODS: TeachingMethod[] = [
  {
    id: 'theory',
    name: 'Theory',
    badgeLabel: 'Primary Style',
    tagline: 'Formal definitions & foundational architectural concepts',
    description:
      'Presents structured principles, syntax definitions, and Java language specifications with clear conceptual frameworks.',
    priorityRank: 1,
    effectivenessPercent: 0,
    successfulUses: 0,
    totalAttempts: 3,
    color: '#0284c7',
    accentBg: '#f0f9ff',
    accentBorder: '#bae6fd',
    accentText: '#0369a1',
    pedagogicalFocus: 'Conceptual blueprints, types, memory hierarchy & invariants',
    aiEscalationRule: 'Default baseline strategy deployed on first introduction of a Java concept.',
    keyStrengths: [
      'Gives rigorous mental models before code implementation',
      'Preferred by structured analytical learners',
      'Establishes correct technical terminology',
    ],
    sampleTrigger: 'Initial question asked or student inquires "What is a Class?"',
  },
  {
    id: 'example',
    name: 'Example',
    badgeLabel: 'Priority #2',
    tagline: 'Concrete Java code snippets & line-by-line execution trace',
    description:
      'Translates abstract syntax into practical, compilable Java snippets showing variable values at each step.',
    priorityRank: 2,
    effectivenessPercent: 0,
    successfulUses: 0,
    totalAttempts: 2,
    color: '#0d9488',
    accentBg: '#f0fdfa',
    accentBorder: '#99f6e4',
    accentText: '#0f766e',
    pedagogicalFocus: 'Syntactic mechanics, input-output demonstration & variable traces',
    aiEscalationRule: 'Escalated when theory fails to clarify syntax mechanics or class layout.',
    keyStrengths: [
      'Bridges high-level concept to actual compile-time code',
      'Provides copy-pasteable patterns for IDE testing',
      'Eliminates confusion about variable scoping',
    ],
    sampleTrigger: 'Student replies "I donâ€™t understand how to write this in Java"',
  },
  {
    id: 'simplified',
    name: 'Simplified',
    badgeLabel: 'Priority #3',
    tagline: 'Plain-language, jargon-free breakdown for quick clarity',
    description:
      'Strips away academic jargon, explaining core logic in short conversational sentences with high readability.',
    priorityRank: 3,
    effectivenessPercent: 0,
    successfulUses: 0,
    totalAttempts: 2,
    color: '#ca8a04',
    accentBg: '#fefce8',
    accentBorder: '#fef08a',
    accentText: '#a16207',
    pedagogicalFocus: 'Cognitive load reduction, core intuition & stripped-down flow',
    aiEscalationRule:
      'Triggered when lexical analysis identifies cognitive fatigue or terminology blockages.',
    keyStrengths: [
      'Breaks down overwhelming paragraphs into bite-sized bullets',
      'Removes intimidating terminology',
      'Fast comprehension turnaround for non-native speakers',
    ],
    sampleTrigger: 'Student message exhibits low lexical variety or confusion markers',
  },
  {
    id: 'analogy',
    name: 'Analogy',
    badgeLabel: 'Priority #4',
    tagline: 'Real-world metaphors & mental bridge illustrations',
    description:
      'Connects challenging computer science concepts to intuitive everyday systems (e.g. blueprint vs constructed house for Class vs Object).',
    priorityRank: 4,
    effectivenessPercent: 0,
    successfulUses: 0,
    totalAttempts: 1,
    color: '#9333ea',
    accentBg: '#faf5ff',
    accentBorder: '#e9d5ff',
    accentText: '#7e22ce',
    pedagogicalFocus: 'Metaphorical transference & relatable domain mapping',
    aiEscalationRule:
      'Deployed as escalation strategy when previous technical explanations do not click.',
    keyStrengths: [
      'Anchors foreign programming models to intuitive daily experiences',
      'High stickiness and emotional recall for tricky paradigms',
      'Proven effective for Object-Oriented polymorphism and inheritance',
    ],
    sampleTrigger: 'Student requests "Explain it like I am 5" or second-cycle confusion',
  },
];

export const POPULATED_TEACHING_METHODS: TeachingMethod[] = [
  {
    ...INITIAL_TEACHING_METHODS[0],
    effectivenessPercent: 78,
    successfulUses: 14,
    totalAttempts: 18,
    priorityRank: 1,
    badgeLabel: 'Most Effective Â· Rank #1',
  },
  {
    ...INITIAL_TEACHING_METHODS[1],
    effectivenessPercent: 65,
    successfulUses: 11,
    totalAttempts: 17,
    priorityRank: 2,
    badgeLabel: 'High Impact Â· Rank #2',
  },
  {
    ...INITIAL_TEACHING_METHODS[3],
    effectivenessPercent: 54,
    successfulUses: 7,
    totalAttempts: 13,
    priorityRank: 3,
    badgeLabel: 'Emerging Â· Rank #3',
  },
  {
    ...INITIAL_TEACHING_METHODS[2],
    effectivenessPercent: 42,
    successfulUses: 5,
    totalAttempts: 12,
    priorityRank: 4,
    badgeLabel: 'Secondary Â· Rank #4',
  },
];

export const MOCK_STUDENT: StudentProfile = {
  studentId: 'stu_java_8492',
  name: 'Alex Rivera',
  course: 'IT-304: Advanced Java & OOP',
  studyTrack: 'Adaptive Voice Tutoring Cohort',
  sessionDuration: '38 mins active',
};
