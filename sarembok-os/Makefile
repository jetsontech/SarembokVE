.PHONY: all sim-test sim-run verify-claims kernel clean

all: sim-test

sim-test:
	@python3 sim/run_tests.py

sim-run:
	@python3 sim/shell.py

verify-claims:
	@bash tools/claim-verify/verify.sh

kernel:
	@echo "[kernel] seL4 port target ? requires seL4 toolchain"
	@echo "See docs/ANTIGRAVITY.md. Do not fake this build."

clean:
	@rm -rf sim/__pycache__ sim/*.wal sim/*.db
