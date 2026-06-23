#!/usr/bin/env sh
set -eu

if command -v mutmut >/dev/null 2>&1; then
  echo "mutmut is installed; run it with this repository's survivor policy in tests/mutation-survivors.md."
  echo "Suggested command:"
  echo "  mutmut run --paths-to-mutate tools/spec_runner.py,tools/plugin_runner.py"
  echo
  echo "After the run, classify every survivor touching safety-relevant code."
else
  echo "mutmut is not installed; running the deterministic invariant fuzzer as the non-blocking mutation smoke check."
  echo "Install mutmut in a throwaway dev environment for full mutation scoring."
fi

python3 tests/test_invariant_fuzz.py --cases "${FUZZ_CASES:-2000}"
