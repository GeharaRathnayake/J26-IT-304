/**
 * Runtime validation at the transport boundary (ADR FE-06).
 *
 * TypeScript types vanish at runtime. The response passes through the tutor
 * service AND (in `express` mode) a teammate's server, so a renamed field would
 * otherwise surface as a blank badge rather than an error — and blank badges get
 * discovered on demo day. These schemas also serve as executable contract
 * documentation for the Express teammate.
 */

import { z } from 'zod';
import { TutorError } from './errors';
import type { EpisodeLog, HealthResponse, ModelInfo, TopicOption, TutorResponse } from './types';

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

export const strategySchema = z.enum(['theory', 'example', 'simplified', 'analogy']);
export const triggerSchema = z.enum(['default', 'confusion', 'request', 'personalised']);
export const actionSchema = z.enum([
  'explain',
  'resolved',
  'offer_new_cycle',
  'end_unresolved',
  'clarify',
]);
export const labelSchema = z.enum(['confused', 'understood']);
export const sourceSchema = z.enum(['rule', 'model']);
export const outcomeSchema = z.enum(['resolved', 'end_unresolved']);

/** snake_case slug, as produced by the service's topic list. */
export const topicIdSchema = z.string().regex(/^[a-z][a-z0-9_]*$/, 'topic must be a snake_case slug');

export const topicOptionSchema = z.object({
  id: topicIdSchema,
  label: z.string().min(1),
});

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export const historyTurnSchema = z.object({
  role: z.enum(['student', 'tutor']),
  text: z.string(),
  strategy: strategySchema.optional(),
  ts: z.string(),
});

export const strategyUseSchema = z.object({
  strategy: strategySchema,
  trigger: triggerSchema,
});

export const tutorStateSchema = z.object({
  episode_id: z.string().min(1),
  cycle: z.number().int().positive(),
  strategies_used: z.array(strategyUseSchema),
  awaiting_cycle_confirmation: z.boolean(),
  prior_explanations: z.array(z.string()),
});

// ---------------------------------------------------------------------------
// Episode log
// ---------------------------------------------------------------------------

export const deliverySchema = z.object({
  seq: z.number().int().positive(),
  strategy: strategySchema,
  trigger: triggerSchema,
  cycle: z.number().int().positive(),
  student_label: labelSchema,
  probability: z.number().min(0).max(1),
  source: sourceSchema,
});

export const episodeLogSchema = z.object({
  schema_version: z.literal('1.0'),
  episode_id: z.string().min(1),
  student_id: z.string().min(1),
  topic: topicIdSchema,
  started_at: z.string(),
  ended_at: z.string(),
  outcome: outcomeSchema,
  cycles: z.number().int().positive(),
  deliveries: z.array(deliverySchema),
  counted_strategies: z.number().int().nonnegative(),
  requested_strategies: z.number().int().nonnegative(),
  winning_strategy: strategySchema.nullable(),
  winning_combination: z.array(strategySchema),
  is_weak: z.boolean(),
  weak_rule: z.string(),
  model_version: z.string(),
});

// ---------------------------------------------------------------------------
// Response
// ---------------------------------------------------------------------------

export const confusionResultSchema = z.object({
  label: labelSchema,
  probability: z.number().min(0).max(1),
  source: sourceSchema,
});

export const latencyBreakdownSchema = z.object({
  classify: z.number().nonnegative(),
  llm: z.number().nonnegative(),
  total: z.number().nonnegative(),
});

export const responseMetaSchema = z.object({
  model_version: z.string(),
  llm: z.string(),
  latency_ms: latencyBreakdownSchema,
  fallback: z.boolean().optional(),
});

export const tutorResponseSchema = z
  .object({
    request_id: z.string().min(1),
    confusion: confusionResultSchema,
    detected_request: strategySchema.nullable(),
    action: actionSchema,
    strategy: strategySchema.nullable(),
    trigger: triggerSchema.nullable(),
    response: z.string(),
    updated_state: tutorStateSchema,
    episode_log: episodeLogSchema.nullable(),
    meta: responseMetaSchema,
  })
  // Cross-field rules the contract implies but a flat schema would not catch.
  // These are the invariants the UI actually depends on, so they are worth
  // enforcing rather than trusting.
  .superRefine((res, ctx) => {
    const episodeEnded = res.action === 'resolved' || res.action === 'end_unresolved';

    if (episodeEnded && res.episode_log === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['episode_log'],
        message: `episode_log must be present when action is "${res.action}"`,
      });
    }

    if (!episodeEnded && res.episode_log !== null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['episode_log'],
        message: `episode_log must be null when action is "${res.action}"`,
      });
    }

    if (res.action === 'explain' && res.strategy === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['strategy'],
        message: 'strategy must be present when action is "explain"',
      });
    }
  });

export const healthResponseSchema = z.object({
  status: z.enum(['ok', 'degraded']),
  model_loaded: z.boolean(),
  llm_reachable: z.boolean(),
  model_version: z.string().nullable(),
});

export const modelInfoSchema = z.object({
  version: z.string(),
  trained_at: z.string(),
  dataset: z.string(),
  threshold: z.number(),
  metrics: z.record(z.string(), z.number()),
});

export const topicsResponseSchema = z.array(topicOptionSchema).min(1);

// ---------------------------------------------------------------------------
// Parse helpers — every one throws a TutorError('contract') on failure
// ---------------------------------------------------------------------------

function parseOrThrow<T>(schema: z.ZodType<T>, data: unknown, what: string): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new TutorError('contract', `Malformed ${what} from tutor service`, {
      detail: result.error.issues,
    });
  }
  return result.data;
}

export function parseTutorResponse(data: unknown, expectedRequestId?: string): TutorResponse {
  const parsed = parseOrThrow(tutorResponseSchema, data, 'tutor response') as TutorResponse;

  // A mismatched request_id means responses are being crossed somewhere in the
  // chain. Cheap to check, and extremely confusing to debug if not caught here.
  if (expectedRequestId !== undefined && parsed.request_id !== expectedRequestId) {
    throw new TutorError('contract', 'request_id mismatch in tutor response', {
      detail: { expected: expectedRequestId, received: parsed.request_id },
    });
  }

  return parsed;
}

export const parseEpisodeLog = (d: unknown): EpisodeLog =>
  parseOrThrow(episodeLogSchema, d, 'episode log') as EpisodeLog;

export const parseHealth = (d: unknown): HealthResponse =>
  parseOrThrow(healthResponseSchema, d, 'health response');

export const parseModelInfo = (d: unknown): ModelInfo =>
  parseOrThrow(modelInfoSchema, d, 'model info');

export const parseTopics = (d: unknown): TopicOption[] =>
  parseOrThrow(topicsResponseSchema, d, 'topics response');
