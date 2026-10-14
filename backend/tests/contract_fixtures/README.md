# Contract fixtures

Byte-for-byte copies of the frontend's frozen contract fixtures, under
`dev/frontend/src/features/tutor/api/fixtures/`:

| Copy here | Source |
|---|---|
| `topics.json` | `dev/frontend/src/features/tutor/api/fixtures/topics.json` |
| `episode-log.json` | `dev/frontend/src/features/tutor/api/fixtures/episode-log.json` |

They exist because the Docker build context is `dev/backend/` only, so tests running in the
container cannot read `dev/frontend/`. **Never edit them by hand.** If a frontend fixture
changes (a contract change agreed with the frontend), re-copy the file. The drift-guard tests
(`test_fixture_copy_matches_frontend_source` and `test_episode_log_fixture_copy_matches_frontend_source`)
fail in the venv when a copy differs from its source, and skip with a visible reason in Docker.
`.gitattributes` marks this directory `-text` so Git does not rewrite line endings.
