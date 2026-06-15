# Public base URL for generated docs
BASE_URL ?= https://docs.example.com

# Local path to docs.json or docs root directory
DOCS_ROOT ?= .

# Optional navigation types. Supports: tabs, anchors, groups, and pages
NAV_TYPE ?=

# Command used to run the llms.txt generator
LLMS_TXT := uv run python scripts/llms_txt

# Base CLI arguments shared by all runs
LLMS_ARGS := --base-url $(BASE_URL) --docs-root $(DOCS_ROOT)

# Conditionally append navigation flag only if NAV_TYPE is set
ifneq ($(strip $(NAV_TYPE)),)
LLMS_ARGS += --nav-type $(NAV_TYPE)
endif

.PHONY: help
help: ## Show help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  BASE_URL   Public docs URL (default: $(BASE_URL))"
	@echo "  DOCS_ROOT  Path to docs.json (default: $(DOCS_ROOT))"
	@echo "  NAV_TYPE   Navigation type: tabs, anchors, groups, or pages"

.PHONY: generate-llms-txt
generate-llms-txt: ## Generate llms.txt files for a navigation type
	$(LLMS_TXT) $(LLMS_ARGS)
