#!/bin/bash
# SessionStart hook: install the markov-hedge-fund-method skill into ~/.claude/skills/
# so the Stooq-fallback Markov regime model is available in every new web session.
#
# Idempotent: re-runs are a no-op unless the source files in the repo have changed
# or the venv is missing.

set -euo pipefail

SKILL_NAME="markov-hedge-fund-method"
REPO_SKILL_SRC="$CLAUDE_PROJECT_DIR/claude-skills/$SKILL_NAME"
INSTALL_DIR="$HOME/.claude/skills/$SKILL_NAME"

# Only act in the remote (web) execution environment — local installs should be
# managed by the user, not auto-overwritten by this hook.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if [ ! -d "$REPO_SKILL_SRC" ]; then
  echo "session-start-hook: skill source not found at $REPO_SKILL_SRC — skipping."
  exit 0
fi

mkdir -p "$HOME/.claude/skills"

# Sync source files (no .venv, no lock files) from repo into ~/.claude/skills/.
# rsync if available (preferred — diff-aware); otherwise plain cp -R.
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.egg-info' \
    --exclude 'uv.lock' \
    --exclude '.hmm_available' \
    "$REPO_SKILL_SRC/" "$INSTALL_DIR/"
else
  mkdir -p "$INSTALL_DIR"
  cp -R "$REPO_SKILL_SRC/." "$INSTALL_DIR/"
fi

# Ensure uv is available.
if ! command -v uv >/dev/null 2>&1; then
  echo "session-start-hook: uv not found, installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
fi

cd "$INSTALL_DIR"

# Create Python 3.12 venv if missing.
if [ ! -d ".venv" ]; then
  echo "session-start-hook: creating Python 3.12 venv..."
  uv python install 3.12 >/dev/null 2>&1 || true
  uv venv --python 3.12 .venv
fi

# Install required deps (uv pip install is fast on warm cache; idempotent).
echo "session-start-hook: installing required deps..."
uv pip install "yfinance>=0.2" "numpy>=1.26" "pandas>=2.0" "scikit-learn>=1.4" >/dev/null

# Attempt optional HMM extension — never fail the hook on this.
if uv pip install "hmmlearn>=0.3" >/dev/null 2>&1; then
  echo "true" > "$INSTALL_DIR/.hmm_available"
  echo "session-start-hook: HMM extension installed."
else
  echo "false" > "$INSTALL_DIR/.hmm_available"
  echo "session-start-hook: HMM extension skipped (optional)."
fi

echo "session-start-hook: $SKILL_NAME ready at $INSTALL_DIR"
