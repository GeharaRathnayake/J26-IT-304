/**
 * Contract tests (frontendPlan/08_TESTING.md §1).
 *
 * These assert that the schemas accept the sample payloads documented in
 * `ARCHITECTURE.md` §7.2/§7.3 and reject malformed variants. The same fixtures
 * are used by the mock transport and should be used by the Express teammate's
 * contract tests, so a contract change breaks a test immediately rather than
 * being discovered during integration (PRD R6).
 */

import { describe, expect, it } from 'vitest';

import explainFixture from './fixtures/tutor-response.explain.json';
import resolvedFixture from './fixtures/tutor-response.resolved.json';
import episodeLogFixture from './fixtures/episode-log.json';
import topicsFixture from './fixtures/topics.json';

import {
  episodeLogSchema,
  parseEpisodeLog,
  parseTopics,
  parseTutorResponse,
  tutorResponseSchema,
} from './schemas';
import { TutorError } from './errors';
import { FALLBACK_TOPICS } from '../config/topics';

describe('documented sample payloads', () => {
  it('accepts the ARCHITECTURE §7.2 explain response', () => {
    expect(() => parseTutorResponse(explainFixture)).not.toThrow();
  });

  it('accepts a resolved response carrying an episode log', () => {
    const res = parseTutorResponse(resolvedFixture);
    expect(res.action).toBe('resolved');
    expect(res.episode_log).not.toBeNull();
    expect(res.episode_log?.winning_strategy).toBe('analogy');
  });

  it('accepts the ARCHITECTURE §7.3 episode log', () => {
    const log = parseEpisodeLog(episodeLogFixture);
    expect(log.schema_version).toBe('1.0');
  });

  it('accepts the topics list', () => {
    expect(parseTopics(topicsFixture)).toHaveLength(14);
  });
});

describe('request_id checking', () => {
  it('passes when the id matches', () => {
    expect(() =>
      parseTutorResponse(explainFixture, explainFixture.request_id),
    ).not.toThrow();
  });

  it('throws a contract error when responses are crossed', () => {
    expect(() => parseTutorResponse(explainFixture, 'some-other-id')).toThrowError(TutorError);
  });
});

describe('cross-field invariants the UI depends on', () => {
  it('rejects an ended episode with a null log', () => {
    const bad = { ...resolvedFixture, episode_log: null };
    expect(tutorResponseSchema.safeParse(bad).success).toBe(false);
  });

  it('rejects a mid-episode response that carries a log', () => {
    const bad = { ...explainFixture, episode_log: episodeLogFixture };
    expect(tutorResponseSchema.safeParse(bad).success).toBe(false);
  });

  it('rejects an explain action with no strategy', () => {
    const bad = { ...explainFixture, strategy: null };
    expect(tutorResponseSchema.safeParse(bad).success).toBe(false);
  });
});

describe('malformed payloads', () => {
  it('rejects an unknown strategy', () => {
    const bad = { ...explainFixture, strategy: 'metaphor' };
    expect(tutorResponseSchema.safeParse(bad).success).toBe(false);
  });

  it('rejects a probability outside [0, 1]', () => {
    const bad = { ...explainFixture, confusion: { label: 'confused', probability: 1.4, source: 'model' } };
    expect(tutorResponseSchema.safeParse(bad).success).toBe(false);
  });

  it('rejects a non-snake_case topic slug', () => {
    const bad = { ...episodeLogFixture, topic: 'Exception Handling' };
    expect(episodeLogSchema.safeParse(bad).success).toBe(false);
  });

  it('rejects an unversioned episode log', () => {
    const { schema_version: _dropped, ...bad } = episodeLogFixture;
    expect(episodeLogSchema.safeParse(bad).success).toBe(false);
  });

  it('surfaces Zod issues as TutorError detail for the Research Panel', () => {
    try {
      parseEpisodeLog({ episode_id: 'x' });
      expect.unreachable('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(TutorError);
      expect((err as TutorError).kind).toBe('contract');
      expect(Array.isArray((err as TutorError).detail)).toBe(true);
    }
  });
});

describe('topic list drift guard (10_DECISIONS.md Q1)', () => {
  it('frontend fallback list matches the service list exactly', () => {
    // NOTE: both sides of this comparison live in the frontend, so until
  // app/topics.py exists this is a self-consistency check, not a check against
  // the service. It only guards against drift if fixtures/topics.json is kept
  // as the service's mirror (guide §10, item 14).
  // The service owns the list (app/topics.py). If this fails, the static copy
    // in config/topics.ts has drifted and requests for the drifted topic will
    // 422 at runtime.
    expect(FALLBACK_TOPICS).toEqual(topicsFixture);
  });
});
