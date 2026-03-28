SKILL_DIR := $(HOME)/.claude/skills/jetcite-skill
VERSION := $(shell python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")

.PHONY: deploy-skill

deploy-skill:
	rsync -a --delete --exclude='__pycache__' src/jetcite/ $(SKILL_DIR)/src/jetcite/
	cp jetcite_tool.py check_update.py SKILL.md $(SKILL_DIR)/
	@printf '[project]\nname = "jetcite-skill"\nversion = "%s"\n' "$(VERSION)" > $(SKILL_DIR)/pyproject.toml
	@echo "Deployed jetcite skill v$(VERSION) to $(SKILL_DIR)"
