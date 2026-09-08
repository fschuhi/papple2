# --- OS-specific variables ---
ifeq ($(OS),Windows_NT)
    VENV_DIR = .venv-win
    VENV_BIN = $(VENV_DIR)/Scripts
    PYTHON   = py -3
else
    VENV_DIR = .venv
    VENV_BIN = $(VENV_DIR)/bin
    PYTHON   = python3
endif

# --- Derived variables (shared) ---
VENV_ACTIVATE = $(VENV_BIN)/activate
ACTIVATE      = . $(VENV_ACTIVATE)
PIP           = $(ACTIVATE) && pip
RUN           = $(ACTIVATE) && python
SETUP_STAMP   = $(VENV_DIR)/.setup_stamp

# --- Phony targets ---
.PHONY: all setup test test-verbose run clean showtree gentree filesdump filesdump-detailed help

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

# --- Run Target ---
run: $(SETUP_STAMP) ## Run the Robotron emulator with the pygame window
	$(RUN) -m papple2.Robotron

# --- Utility Targets ---
clean: ## Remove venv, cache, and tmp files
	rm -rf $(VENV_DIR) .pytest_cache tmp
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.egg-info" -type d -prune -exec rm -rf {} +

showtree: ## Show project directory structure
	tree -I ".venv|.venv-win|__pycache__|.idea|.pytest_cache|*egg-info|tmp"

gentree: ## Save tree structure to file
	mkdir -p tmp
	tree -I ".venv|.venv-win|__pycache__|.idea|.pytest_cache|*egg-info|tmp" > tmp/project_tree.txt

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
