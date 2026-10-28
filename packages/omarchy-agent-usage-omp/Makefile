# Makefile for the omp collector.
#
# Targets:
#   make test      - run the contract test against the real ~/.omp tree
#   make install   - sudo copy the script into /usr/share/omarchy/bin/ so the
#                    omarchy-agent-usage-update picker discovers it
#   make record    - regenerate ~/.local/state/omarchy/agents/usage/omp.json
#                    (run after install or after collecting new sessions)
#   make uninstall - remove the collector from /usr/share/omarchy/bin/

PREFIX  ?= /usr/share/omarchy
BIN     := $(PREFIX)/bin
SCRIPT  := omarchy-agent-usage-omp
DEST    := $(BIN)/$(SCRIPT)

.PHONY: test install record uninstall

test:
	./tests/test_contract.py

install:
	sudo install -m 755 $(SCRIPT) $(DEST)
	@echo "Installed to $(DEST)"

record:
	omarchy agent usage-update --force omp
	@echo "Wrote $$(echo $$XDG_STATE_HOME)/omarchy/agents/usage/omp.json (or ~/.local/state/...)"

uninstall:
	sudo rm -f $(DEST)
	@echo "Removed $(DEST)"