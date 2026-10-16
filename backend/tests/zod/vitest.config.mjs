// A plain object, no imports: this file lives outside dev/frontend/, where `vitest/config` would not
// resolve. `globals: true` because the test cannot import vitest either.
export default {
  test: {
    globals: true,
    environment: 'node',
    include: ['zod_contract.test.ts'],
  },
};
