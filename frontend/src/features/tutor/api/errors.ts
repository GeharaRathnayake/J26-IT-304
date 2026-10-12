/**
 * Error taxonomy for the tutor transport. Maps to `frontendPlan/06_CROSS_CUTTING.md` §1.
 *
 * The distinction that matters: `ContractError` means the backend and frontend
 * disagree about the shape of the data. That is a developer-facing bug, must be
 * loud in development, and must never be silently rendered as a blank badge.
 */

export type TutorErrorKind =
  /** 503 — model artifact not loaded; service is unhealthy. */
  | 'model_unavailable'
  /** 504 — LLM timed out and no fallback was available. */
  | 'llm_timeout'
  /** 422 — request failed validation. Indicates contract drift. */
  | 'validation'
  /** Response did not match the Zod schema, or `request_id` mismatched. */
  | 'contract'
  /** Network failure, DNS, CORS, offline. */
  | 'network'
  /** Anything else. */
  | 'unknown';

export class TutorError extends Error {
  readonly kind: TutorErrorKind;
  /** HTTP status, when there was one. */
  readonly status?: number;
  /** Developer-facing detail (e.g. a Pydantic error body or a Zod issue list).
   *  Shown in the Research Panel, never to the student. */
  readonly detail?: unknown;

  constructor(
    kind: TutorErrorKind,
    message: string,
    options?: { status?: number; detail?: unknown; cause?: unknown },
  ) {
    super(message, options?.cause !== undefined ? { cause: options.cause } : undefined);
    this.name = 'TutorError';
    this.kind = kind;
    if (options?.status !== undefined) this.status = options.status;
    if (options?.detail !== undefined) this.detail = options.detail;
  }

  /** Generic, non-alarming text for the student. Detail stays in the panel. */
  get studentMessage(): string {
    switch (this.kind) {
      case 'model_unavailable':
        return 'The tutor is not available right now.';
      case 'llm_timeout':
        return 'That took too long to answer. Try sending it again.';
      case 'network':
        return 'Connection lost. Your message is still here — try again.';
      case 'validation':
      case 'contract':
      case 'unknown':
      default:
        return 'Something went wrong. Try again.';
    }
  }

  /** True when retrying the same turn is sensible and safe. */
  get isRetryable(): boolean {
    return this.kind === 'llm_timeout' || this.kind === 'network';
  }
}

export function mapStatusToKind(status: number): TutorErrorKind {
  if (status === 503) return 'model_unavailable';
  if (status === 504) return 'llm_timeout';
  if (status === 422) return 'validation';
  return 'unknown';
}
