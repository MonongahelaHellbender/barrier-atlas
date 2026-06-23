#!/usr/bin/env sh
set -eu

python3 tools/toolchain_check.py
python3 -m py_compile \
  tools/barrier_check.py \
  tools/atlas_log.py \
  tools/plugin_runner.py \
  tools/sandbox.py \
  tools/sign_record.py \
  tools/signing_common.py \
  tools/spec_runner.py \
  tools/to_intoto.py \
  tools/verify_record.py \
  tools/checkers/rup_plugin_alt.py \
  spec/validate.py \
  spec/conformance/run_conformance.py \
  tests/test_phase_e_attestation.py \
  tests/test_invariant_fuzz.py
python3 spec/validate.py
python3 spec/conformance/run_conformance.py --runner "python3 tools/plugin_runner.py"
python3 tests/test_phase_e_attestation.py
python3 tests/test_invariant_fuzz.py
python3 tests/test_one_directional.py
python3 tools/barrier_check.py
