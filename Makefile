help: ## Show this help!
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

setup: ## Setup the environment and install all required dependencies
	poetry install

test: ## Execute all unit tests
	poetry run pytest tests -v

release: ## Create a Release in Github
	@echo "gh release create v0.x.x --notes \"Bugfix Release\""
