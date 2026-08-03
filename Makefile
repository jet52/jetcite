VERSION := $(shell python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
SKILL_DIR := skill
DIST_NAME := jetcite-skill-v$(VERSION)

PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: deploy-skill package clean test version-check

# The version lives in four places that must agree:
#   pyproject.toml            canonical — drives VERSION above, the dist zip
#                             name, and the generated skill/pyproject.toml that
#                             check_update.py reads
#   src/jetcite/_version.py   the library's runtime version, vendored verbatim
#                             into jetmemo and jetredline
#   .claude-plugin/plugin.json  the plugin manifest
#   skill/SKILL.md            the frontmatter the model reads
#
# v2.8.0 was first cut with only _version.py bumped, leaving pyproject.toml at
# 2.7.4 and silently re-locking uv.lock to the stale value; plugin.json had
# meanwhile drifted to 2.5.3 and SKILL.md to 1.4.1. This makes that class of
# failure loud instead of silent, as it already is in jetmemo and jetredline.
version-check:
	@V=$(VERSION) && \
	LV=$$(sed -n 's/^__version__[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' src/jetcite/_version.py | head -1) && \
	PV=$$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' .claude-plugin/plugin.json | head -1) && \
	SV=$$(sed -n 's/^version:[[:space:]]*//p' skill/SKILL.md | head -1) && \
	if [ "$$V" != "$$LV" ] || [ "$$V" != "$$PV" ] || [ "$$V" != "$$SV" ]; then \
	  echo "VERSION DRIFT: pyproject.toml=$$V _version.py=$$LV plugin.json=$$PV SKILL.md=$$SV"; exit 1; \
	fi; \
	echo "version: $$V consistent across pyproject.toml, _version.py, plugin.json, SKILL.md."

# Generate the lightweight pyproject.toml that check_update.py reads
$(SKILL_DIR)/pyproject.toml: pyproject.toml
	@printf '[project]\nname = "jetcite-skill"\nversion = "%s"\n' "$(VERSION)" > $@

# Deploy skill to ~/.claude/skills/ (only needed on machines without symlink setup)
deploy-skill: $(SKILL_DIR)/pyproject.toml
	rsync -a --delete --exclude='__pycache__' --exclude='src' $(SKILL_DIR)/ $(HOME)/.claude/skills/jetcite-skill/
	rsync -a --delete --exclude='__pycache__' src/jetcite/ $(HOME)/.claude/skills/jetcite-skill/src/jetcite/
	@echo "Deployed jetcite skill v$(VERSION)"

test: version-check
	$(PYTHON) -m pytest tests/ -q

# Package skill for distribution. version-check first so a drifted version can
# never be shipped — the zip name comes from pyproject.toml, but consumers read
# _version.py, plugin.json, and SKILL.md.
package: version-check $(SKILL_DIR)/pyproject.toml
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
