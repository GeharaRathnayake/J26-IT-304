/**
 * Java topic list (10_DECISIONS.md Q1).
 *
 * ⚠ OWNERSHIP: the tutor service owns this list in `app/topics.py` and exposes
 * it via `GET /topics`. THIS IS A FALLBACK COPY, not a parallel truth:
 *
 *   1. On mount, a successful `transport.topics()` REPLACES this list.
 *   2. The service returns 422 for an unknown slug, so drift between this file
 *      and `app/topics.py` turns into validation errors for that topic.
 *   3. `topics.test.ts` asserts this list matches the service fixture, so drift
 *      fails a test rather than a demo.
 *
 * Provenance: the topics are those offered in the project questionnaire
 * (Proposal Appendix 1.2, Q5 "Which topics in Java do you find most
 * difficult?"), which grounds the list in the requirements gathering rather
 * than making it arbitrary.
 */

import type { TopicOption } from '../api/types';

export const FALLBACK_TOPICS: readonly TopicOption[] = [
  { id: 'variables_and_data_types', label: 'Variables & Data Types' },
  { id: 'conditional_statements', label: 'Conditional Statements' },
  { id: 'loops', label: 'Loops' },
  { id: 'arrays', label: 'Arrays' },
  { id: 'methods_and_functions', label: 'Methods & Functions' },
  { id: 'classes_and_objects', label: 'Classes & Objects' },
  { id: 'inheritance', label: 'Inheritance' },
  { id: 'polymorphism', label: 'Polymorphism' },
  { id: 'encapsulation', label: 'Encapsulation' },
  { id: 'abstraction', label: 'Abstraction' },
  { id: 'exception_handling', label: 'Exception Handling' },
  { id: 'collections', label: 'Collections' },
  { id: 'recursion', label: 'Recursion' },
  { id: 'file_io', label: 'File I/O' },
] as const;

export function topicLabel(id: string, topics: readonly TopicOption[] = FALLBACK_TOPICS): string {
  return topics.find((t) => t.id === id)?.label ?? id;
}
