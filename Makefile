VERSION := $(shell python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
SKILL_DIR := skill
# No "v" before the version: this must match what .github/workflows/release.yml
# publishes, which is what every released asset has been named since v2.5.4.
DIST_NAME := jetcite-skill-$(VERSION)
STAGE := /tmp/jetcite-skill-build

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
# Depends on the generated skill/pyproject.toml (gitignored) so a fresh
# clone creates it and a version bump auto-regenerates it — the sed below
# would otherwise fail on the missing file. The uv.lock check has no such
# self-heal: a stale lock fails the gate until 'uv lock' is run.
version-check: $(SKILL_DIR)/pyproject.toml
	@V=$(VERSION) && \
	LV=$$(sed -n 's/^__version__[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' src/jetcite/_version.py | head -1) && \
	PV=$$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' .claude-plugin/plugin.json | head -1) && \
	SV=$$(sed -n 's/^version:[[:space:]]*//p' skill/SKILL.md | head -1) && \
	if [ "$$V" != "$$LV" ] || [ "$$V" != "$$PV" ] || [ "$$V" != "$$SV" ]; then \
	  echo "VERSION DRIFT: pyproject.toml=$$V _version.py=$$LV plugin.json=$$PV SKILL.md=$$SV"; exit 1; \
	fi; \
	KV=$$(sed -n 's/^version = "\([^"]*\)".*/\1/p' skill/pyproject.toml | head -1) && \
	UV=$$(awk '/^name = "jetcite"$$/{getline; sub(/^version = "/,""); sub(/".*/,""); print; exit}' uv.lock) && \
	if [ "$$V" != "$$KV" ] || [ "$$V" != "$$UV" ]; then \
	  echo "VERSION DRIFT (generated artifacts): skill/pyproject.toml=$$KV uv.lock=$$UV — run 'make skill/pyproject.toml' and 'uv lock'"; exit 1; \
	fi; \
	echo "version: $$V consistent across pyproject.toml, _version.py, plugin.json, SKILL.md, skill/pyproject.toml, uv.lock."

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

# Package skill for distribution. release.yml calls this target, so what you
# build locally is byte-for-byte what gets published — the two used to be
# separate recipes and had silently diverged in three ways (zip name, README,
# and archive layout).
#
# The archive is FLAT: entries sit at the root, with no top-level directory.
# SKILL.md tells the user to "extract the jetcite-skill zip to
# ~/.claude/skills/jetcite-skill/", so a wrapper directory would install one
# level too deep and the skill would not load. Do not "tidy" this into a
# versioned top-level folder.
#
# version-check runs first so a drifted version can never be shipped — the zip
# name comes from pyproject.toml, but consumers read _version.py, plugin.json,
# and SKILL.md.
package: version-check $(SKILL_DIR)/pyproject.toml
	rm -rf $(STAGE)
	mkdir -p $(STAGE)/src
	cp $(SKILL_DIR)/SKILL.md $(SKILL_DIR)/jetcite_tool.py $(SKILL_DIR)/check_update.py $(SKILL_DIR)/pyproject.toml README.md $(STAGE)/
	cp -r src/jetcite $(STAGE)/src/jetcite
	find $(STAGE) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f $(CURDIR)/$(DIST_NAME).zip
	cd $(STAGE) && zip -rq $(CURDIR)/$(DIST_NAME).zip .
	rm -rf $(STAGE)
	@echo "Built: $(DIST_NAME).zip"

clean:
	rm -f jetcite-skill-*.zip $(SKILL_DIR)/pyproject.toml
