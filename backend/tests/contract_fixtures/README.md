# Contract fixtures

`topics.json` is a byte-for-byte copy of

    dev/frontend/src/features/tutor/api/fixtures/topics.json

It exists because the Docker build context is `dev/backend/` only, so tests running in the
container cannot read `dev/frontend/`. **Never edit it by hand.** If the frontend fixture
changes (a contract change agreed with the frontend), re-copy the file; the drift-guard
test (`test_fixture_copy_matches_frontend_source`) fails in the venv when the two differ.
`.gitattributes` marks this directory `-text` so Git does not rewrite its line endings.
