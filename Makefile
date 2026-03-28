VERSION := $(shell python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
SKILL_DIR := skill
DIST_NAME := jetcite-skill-v$(VERSION)

.PHONY: deploy-skill package clean

# Generate the lightweight pyproject.toml that check_update.py reads
$(SKILL_DIR)/pyproject.toml: pyproject.toml
	@printf '[project]\nname = "jetcite-skill"\nversion = "%s"\n' "$(VERSION)" > $@

# Deploy skill to ~/.claude/skills/ (only needed on machines without symlink setup)
deploy-skill: $(SKILL_DIR)/pyproject.toml
	rsync -a --delete --exclude='__pycache__' --exclude='src' $(SKILL_DIR)/ $(HOME)/.claude/skills/jetcite-skill/
	rsync -a --delete --exclude='__pycache__' src/jetcite/ $(HOME)/.claude/skills/jetcite-skill/src/jetcite/
	@echo "Deployed jetcite skill v$(VERSION)"

# Package skill for distribution
package: $(SKILL_DIR)/pyproject.toml
	rm -rf /tmp/$(DIST_NAME)
	mkdir -p /tmp/$(DIST_NAME)/src
	cp -r $(SKILL_DIR)/SKILL.md $(SKILL_DIR)/jetcite_tool.py $(SKILL_DIR)/check_update.py $(SKILL_DIR)/pyproject.toml /tmp/$(DIST_NAME)/
	cp -r src/jetcite /tmp/$(DIST_NAME)/src/jetcite
	find /tmp/$(DIST_NAME) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	cd /tmp && zip -r $(CURDIR)/$(DIST_NAME).zip $(DIST_NAME)/
	rm -rf /tmp/$(DIST_NAME)
	@echo "Built: $(DIST_NAME).zip"

clean:
	rm -f jetcite-skill-*.zip $(SKILL_DIR)/pyproject.toml
