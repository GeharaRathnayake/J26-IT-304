// Runs REAL backend responses (captured by scripts/capture_contract_responses.py) through the
// frontend's own Zod parsers: what the browser does (08 section 3).
//
// The parsers are imported by a path relative to this file (dev/backend/tests/zod -> dev/frontend):
// static, so a moved folder fails loudly at import. `zod` then resolves from the frontend's
// node_modules, because that is where schemas.ts lives. vitest is not imported (globals: true).
// CAPTURE_DIR names the folder holding manifest.json and the captures.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  parseHealth,
  parseModelInfo,
  parseTopics,
  parseTutorResponse,
} from '../../../frontend/src/features/tutor/api/schemas';

const dir = process.env.CAPTURE_DIR;
if (!dir) throw new Error('CAPTURE_DIR is not set');
const manifest: Record<string, { parser: string; request_id?: string }> = JSON.parse(
  readFileSync(join(dir, 'manifest.json'), 'utf-8'),
);

const parsers: Record<string, (data: unknown, requestId?: string) => unknown> = {
  parseTutorResponse: (d, id) => parseTutorResponse(d, id),
  parseTopics: (d) => parseTopics(d),
  parseHealth: (d) => parseHealth(d),
  parseModelInfo: (d) => parseModelInfo(d),
};

describe('real backend responses pass the frontend Zod schemas', () => {
  for (const [file, entry] of Object.entries(manifest)) {
    it(file, () => {
      const parse = parsers[entry.parser];
      if (!parse) throw new Error(`unknown parser ${entry.parser}`);
      const data = JSON.parse(readFileSync(join(dir, file), 'utf-8'));
      expect(() => parse(data, entry.request_id)).not.toThrow();
    });
  }
});
