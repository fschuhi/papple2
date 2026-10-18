# --- Variables (macOS-only: Windows/PyXLL support now lives in probotron) ---
VENV_DIR = .venv
VENV_BIN = $(VENV_DIR)/bin
PYTHON   = python3

# --- Derived variables ---
VENV_ACTIVATE = $(VENV_BIN)/activate
ACTIVATE      = . $(VENV_ACTIVATE)
PIP           = $(ACTIVATE) && pip
RUN           = $(ACTIVATE) && python
SETUP_STAMP   = $(VENV_DIR)/.setup_stamp

# --- Phony targets ---
.PHONY: all setup test test-verbose boot-basic boot-robotron boot-lode-runner boot-lode-runner-break boot-lode-runner-throttled boot-lode-runner-headless boot-bandits lr-count lr-basic-blocks-analysis lr-cross-reference lr-current xrefs-overview xrefs-compress walkthrough walkthrough-md ipython presentation clean showtree gentree commit-hash patch filesdump filesdump-detailed help

all: setup

# --- Virtual Environment Setup ---
$(VENV_ACTIVATE):
	$(PYTHON) -m venv $(VENV_DIR)

$(SETUP_STAMP): $(VENV_ACTIVATE) requirements.txt pyproject.toml
	@echo "--- Installing dependencies ---"
	$(PIP) install -r requirements.txt
	@echo "--- Installing papple2 in editable mode ---"
	$(PIP) install -e .
	@echo "--- Setup complete ---"
	@touch $(SETUP_STAMP)

setup: $(SETUP_STAMP) ## Create venv and install dependencies

# --- Testing Targets ---
test: $(SETUP_STAMP) ## Run all tests (quiet mode)
	$(RUN) -m pytest -q

test-verbose: $(SETUP_STAMP) ## Run tests with verbose output
	$(RUN) -m pytest -v -s

# --- Boot Targets (scripts in scripts/, not part of `make test`) ---
boot-basic: $(SETUP_STAMP) ## Boot Apple II into the Monitor; Ctrl-B enters Integer BASIC
	$(RUN) scripts/boot_basic.py

boot-robotron: $(SETUP_STAMP) ## Boot Robotron with the pygame window
	$(RUN) scripts/boot_robotron.py

boot-lode-runner: $(SETUP_STAMP) ## Boot Lode Runner with the pygame window
	$(RUN) scripts/boot_lode_runner.py data/bin/LODE_RUNNER.BIN

boot-lode-runner-break: $(SETUP_STAMP) ## Boot Lode Runner with the pygame window, stop after 4m instructions
	$(RUN) scripts/boot_lode_runner.py data/bin/LODE_RUNNER.BIN --instructions 4000000

boot-lode-runner-throttled: $(SETUP_STAMP) ## Boot Lode Runner with the pygame window, at the speed of a real Apple II
	$(RUN) scripts/boot_lode_runner.py data/bin/LODE_RUNNER.BIN --speed 1.0

boot-lode-runner-headless: $(SETUP_STAMP) ## Boot Lode Runner headless: print statistics, save both hi-res pages as PNG
	$(RUN) scripts/boot_lode_runner.py data/bin/LODE_RUNNER.BIN --headless

# no headless target: the MLI hook serves every file, so a headless run never stops
boot-bandits: $(SETUP_STAMP) ## Boot Bandits from its Total Replay files with the pygame window
	$(RUN) scripts/boot_bandits.py

# --- Experiment Targets (scripts/lr_*.py, headless; reports in docs/reports/, frozen early ones in tmp/) ---
lr-count: $(SETUP_STAMP) ## Early experiment (frozen): map which addresses Lode Runner's attract play runs (PNG and HTML)
	$(RUN) scripts/lr_count.py data/bin/LODE_RUNNER.BIN

lr-basic-blocks-analysis: $(SETUP_STAMP) ## Experiment: tiling, returns and loop reports (start 0800) of Lode Runner's attract play into docs/reports/lr_basic_blocks_analysis/
	$(RUN) scripts/lr_basic_blocks_analysis.py data/bin/LODE_RUNNER.BIN

lr-cross-reference: $(SETUP_STAMP) ## Experiment: the cross reference of Lode Runner's attract play into docs/reports/lr_cross_reference/, and a summary of it
	$(RUN) scripts/lr_cross_reference.py data/bin/LODE_RUNNER.BIN

lr-current: $(SETUP_STAMP) ## IPython with Lode Runner's current run, built from the committed reports: edit() and show_xrefs() together
	$(ACTIVATE) && ipython -i scripts/lr_current.py

# --- Analysis of `lr_xrefs.csv`
xrefs-overview: $(SETUP_STAMP) ## Very basic analysis of `lr_xrefs.csv`
	$(RUN) scripts/explore_xrefs.py docs/reports/lr_cross_reference/lr_xrefs.csv --top 10

# --- Compress `lr_xrefs.csv` into ranges ---
xrefs-compress: $(SETUP_STAMP) ## Compress contiguous xrefs into ranges
	$(RUN) scripts/compress_xrefs.py docs/reports/lr_cross_reference/lr_xrefs.csv docs/reports/lr_cross_reference/lr_xrefs_compressed.csv

# --- Walkthrough (its programs through the workbench's pipeline, output in tmp/walkthrough/<program>/) ---
walkthrough: $(SETUP_STAMP) ## Run the walkthrough's program nested_loops through tiling and the basic blocks analysis (reports in tmp/walkthrough/nested_loops/)
	$(RUN) scripts/walkthrough.py nested_loops

walkthrough-md: $(SETUP_STAMP) ## Render the walkthrough's chapters (tests/test_walkthrough.py) as tmp/walkthrough/walkthrough.md
	$(RUN) tools/render_walkthrough_md.py

# --- Interactive ---
ipython: $(SETUP_STAMP) ## Start IPython in the venv (e.g. %run scripts/walkthrough.py nested_loops)
	$(ACTIVATE) && ipython

# --- Presentation (the diagrams in docs/diagrams/, rendered by Graphviz's dot) ---
# The SVG goes next to its source, under git, for README.md and docs/;
# PDF and PNG go into tmp/presentation/, for slides.
presentation: ## Render docs/diagrams/*.dot to SVG next to them, and to PDF and PNG in tmp/presentation/
	mkdir -p tmp/presentation
	@for f in docs/diagrams/*.dot; do \
		name=$$(basename $$f .dot); \
		echo "$$f -> docs/diagrams/$$name.svg, tmp/presentation/$$name.pdf, $$name.png"; \
		dot -Tsvg $$f -o docs/diagrams/$$name.svg || exit 1; \
		dot -Tpdf $$f -o tmp/presentation/$$name.pdf || exit 1; \
		dot -Tpng -Gdpi=200 $$f -o tmp/presentation/$$name.png || exit 1; \
	done

# --- Utility Targets ---
clean: ## Remove venv, cache, and tmp files
	rm -rf $(VENV_DIR) .pytest_cache tmp
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +

showtree: ## Show project directory structure
	tree -I ".venv|__pycache__|.idea|.pytest_cache|*egg-info|tmp"

gentree: ## Save tree structure to file
	mkdir -p tmp
	tree -I ".venv|__pycache__|.idea|.pytest_cache|*egg-info|tmp" > tmp/project_tree.txt
	# @if [ -d tmp/applied-patches ]; then tree tmp/applied-patches >> tmp/project_tree.txt; fi

patch: ## apply all *.patch files in the repo root, then move them to tmp/applied-patches/
	@ls *.patch >/dev/null 2>&1 || (echo "No *.patch files in the repo root" && exit 1)
	git apply --check *.patch
	git apply *.patch
	mkdir -p tmp/applied-patches
	mv *.patch tmp/applied-patches/

commit-hash:
	@printf 'Commit hash: `%s`' "$$(git rev-parse --short HEAD)" | pbcopy
	@echo "Commit hash copied to clipboard"

filesdump: $(SETUP_STAMP) gentree ## Create context dump for LLMs
	@if [ -f manifest.lst ]; then \
		$(RUN) tools/concat_files.py manifest.lst > tmp/filesdump.txt; \
		echo "Generated tmp/filesdump.txt"; \
	else \
		echo "Error: manifest.lst not found"; \
	fi

filesdump-detailed: $(SETUP_STAMP) gentree ## Create context dump for LLMs with per-file size details
	@if [ -f manifest.lst ]; then \
		$(RUN) tools/concat_files.py --detailed --sort manifest.lst > tmp/filesdump.txt; \
		echo "Generated tmp/filesdump.txt"; \
	else \
		echo "Error: manifest.lst not found"; \
	fi

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
