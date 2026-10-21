import React, { useState } from 'react';
import type { Strategy } from '../../tutor/api/types';
import type { WeakTopicItem } from '../types';

interface SimulateEpisodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTopicAdded: (newWeakTopic: WeakTopicItem) => void;
}

export const SimulateEpisodeModal: React.FC<SimulateEpisodeModalProps> = ({
  isOpen,
  onClose,
  onTopicAdded,
}) => {
  const [topicName, setTopicName] = useState('Recursion vs Iteration');
  const [studentConfusionQuery, setStudentConfusionQuery] = useState(
    'I keep getting StackOverflowError when running my recursive method. Why does it not stop?'
  );
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationStep, setSimulationStep] = useState<number>(0);

  if (!isOpen) return null;

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setSimulationStep(1);

    setTimeout(() => {
      setSimulationStep(2); // Step 2: Classifier evaluated
    }, 800);

    setTimeout(() => {
      setSimulationStep(3); // Step 3: Escalation engine activated
    }, 1600);

    setTimeout(() => {
      setSimulationStep(4); // Step 4: Breakthrough with Analogy!
      // Create new weak topic item
      const newTopic: WeakTopicItem = {
        id: `sim-${Date.now()}`,
        slug: 'recursion_simulation',
        title: topicName,
        category: 'Core Java Mechanics',
        severity: 'critical',
        status: 'weak',
        cyclesNeeded: 3,
        lastEncountered: 'Just now',
        masteryScore: 40,
        cognitiveBlocker:
          'Missing or unreachable base case; student visualizes recursion as a single running loop rather than stacked active frames.',
        detectedMisconception:
          'Treating recursive call as re-entering same function memory instead of creating a fresh stack frame.',
        commonCompilerOrLogicError: 'java.lang.StackOverflowError',
        recommendedMethod: 'analogy',
        recommendedMethodReason:
          'Russian nesting dolls or cafeteria tray stack analogy visually clarifies frame stacking and unwinding.',
        strategiesAttempted: [
          {
            strategy: 'theory',
            strategyLabel: 'Theory',
            outcome: 'confused',
            timestamp: 'Turn 1',
            tutorExcerpt:
              'Recursion solves problems by having a method call a copy of itself, maintaining state on the JVM call stack until the base condition evaluates to true.',
            studentResponse: studentConfusionQuery,
          },
          {
            strategy: 'example',
            strategyLabel: 'Code Example',
            outcome: 'confused',
            timestamp: 'Turn 2',
            tutorExcerpt:
              '`public static int fact(int n) { if (n <= 1) return 1; return n * fact(n - 1); }`',
            studentResponse: '"Where does the number wait while the next fact() is running?"',
          },
          {
            strategy: 'analogy',
            strategyLabel: 'Analogy',
            outcome: 'breakthrough',
            timestamp: 'Turn 3',
            tutorExcerpt:
              'Think of a stack of cafeteria trays or Russian nesting dolls! You cannot open the smallest doll until you first open all outer ones. Each recursive call places a new tray on top. Once you hit the base case, you start taking trays off one by one and combining the answers!',
            studentResponse: '"Now I see why missing the base case crashes the memory! The tray pile hits the ceiling!"',
          },
        ],
        explanationSamples: {
          analogy: {
            strategy: 'analogy',
            title: 'Analogy: Cafeteria Tray Stack & Russian Dolls',
            subtitle: 'Visualizing stack memory',
            content:
              'Think of recursion like writing down a task on a sticky note and placing it on a stack of trays. You cannot finish Tray #1 until Tray #2 is done. When you hit the base case, you grab the final answer and work your way backwards down the stack.',
          },
          example: {
            strategy: 'example',
            title: 'Base Case Code Demo',
            subtitle: 'Factorial execution',
            content: 'Tracing call stack returns:',
            codeSnippet: `int count(int n) {
    if (n == 0) return 0; // BASE CASE!
    return n + count(n - 1);
}`,
          },
          simplified: {
            strategy: 'simplified',
            title: 'Two Non-Negotiable Rules',
            subtitle: 'Preventing StackOverflowError',
            content:
              '1. Every recursive function MUST have an if-statement that does NOT call itself (Base Case).\n2. Every call MUST move closer to that base condition.',
          },
          theory: {
            strategy: 'theory',
            title: 'Call Stack Allocation Semantics',
            subtitle: 'Thread Execution Stack Frames',
            content:
              'Each invocation creates a distinct activation record on the thread\'s call stack storing local variables and return addresses. Unbounded recursion exhausts JVM `-Xss` memory capacity.',
          },
        },
        practiceQuestion: {
          question: 'What occurs if a recursive function has no base case?',
          options: [
            'It automatically halts after 100 iterations.',
            'A java.lang.StackOverflowError is thrown when call stack space is exhausted.',
            'It behaves like an empty while loop.',
            'The compiler rejects it at compile time.',
          ],
          correctIndex: 1,
          explanation:
            'Without a base case, endless method activation records are placed on the JVM thread stack until memory limit is breached.',
        },
      };

      onTopicAdded(newTopic);
      setIsSimulating(false);
    }, 2500);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-3xl border border-[#d6e7e3] shadow-2xl max-w-xl w-full p-6 md:p-8 space-y-5">
        <div className="flex items-center justify-between border-b border-[#edf4f2] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#e6f7f3] text-[#0ca58e] flex items-center justify-center font-extrabold text-lg">
              âš¡
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[#11312b]">
                Simulate Tutoring Escalation Episode
              </h3>
              <p className="text-xs text-[#527771] font-medium">
                Watch the research engine classify confusion and escalate strategies
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-[#edf5f3] hover:bg-[#dfeeed] text-[#345b54] flex items-center justify-center font-bold"
          >
            âœ•
          </button>
        </div>

        {/* Input Fields */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-[#143d36] mb-1.5">
              Java Topic Name:
            </label>
            <input
              type="text"
              value={topicName}
              onChange={(e) => setTopicName(e.target.value)}
              disabled={isSimulating}
              className="w-full px-3.5 py-2.5 bg-[#f4f9f7] rounded-xl border border-[#cfe1dc] text-xs font-semibold text-[#11332d] focus:border-[#0ca58e] focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[#143d36] mb-1.5">
              Simulated Student Question / Confusion Query:
            </label>
            <textarea
              value={studentConfusionQuery}
              onChange={(e) => setStudentConfusionQuery(e.target.value)}
              disabled={isSimulating}
              rows={3}
              className="w-full px-3.5 py-2.5 bg-[#f4f9f7] rounded-xl border border-[#cfe1dc] text-xs font-semibold text-[#11332d] focus:border-[#0ca58e] focus:outline-none"
            />
          </div>
        </div>

        {/* Live Simulation Progress Stepper */}
        {simulationStep > 0 && (
          <div className="p-4 bg-[#f0f8f6] border border-[#cae5df] rounded-2xl space-y-2 text-xs">
            <div className="font-bold text-[#113d35] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#0ca58e] animate-ping" />
              <span>Real-Time Engine Telemetry:</span>
            </div>

            <div className="space-y-1.5">
              <div
                className={`flex items-center gap-2 ${
                  simulationStep >= 1 ? 'text-[#0ca58e] font-bold' : 'text-[#8daaa4]'
                }`}
              >
                <span>{simulationStep >= 1 ? 'âœ“' : 'â—‹'}</span>
                <span>1. Rule Layer & TF-IDF Classifier: Confusion detected (p = 0.89)</span>
              </div>
              <div
                className={`flex items-center gap-2 ${
                  simulationStep >= 2 ? 'text-[#0ca58e] font-bold' : 'text-[#8daaa4]'
                }`}
              >
                <span>{simulationStep >= 2 ? 'âœ“' : 'â—‹'}</span>
                <span>2. Escalation Engine: Prior Theory failed; Escalating to Rank #1 (Analogy)</span>
              </div>
              <div
                className={`flex items-center gap-2 ${
                  simulationStep >= 3 ? 'text-[#0ca58e] font-bold' : 'text-[#8daaa4]'
                }`}
              >
                <span>{simulationStep >= 3 ? 'âœ“' : 'â—‹'}</span>
                <span>3. Local Ollama LLM (llama3.2:3b): Synthesizing Tray Stack Analogy</span>
              </div>
              <div
                className={`flex items-center gap-2 ${
                  simulationStep >= 4 ? 'text-emerald-700 font-extrabold' : 'text-[#8daaa4]'
                }`}
              >
                <span>{simulationStep >= 4 ? 'ðŸŽ‰' : 'â—‹'}</span>
                <span>4. Breakthrough Achieved! Stored in "Weakness topic area" (FR-16)</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isSimulating}
            className="px-4 py-2 bg-white text-[#345b54] text-xs font-bold rounded-xl border border-[#d2e3df] hover:bg-[#f0f7f5]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleRunSimulation}
            disabled={isSimulating}
            className="px-6 py-2.5 bg-gradient-to-r from-[#0ca58e] to-[#078572] hover:from-[#0dae96] hover:to-[#099580] text-white text-xs font-bold rounded-xl shadow-md transition-all disabled:opacity-50"
          >
            {isSimulating ? 'Processing Escalation...' : 'Run Simulation Episode âš¡'}
          </button>
        </div>
      </div>
    </div>
  );
};
