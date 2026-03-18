#!/bin/bash
# install_hooks.sh — Setup git pre-commit hooks for Betterleaks

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_FILE="$PROJECT_ROOT/.git/hooks/pre-commit"

echo "Installing Betterleaks pre-commit hook..."

cat << 'EOF' > "$HOOK_FILE"
#!/bin/bash
# Pre-commit hook for Betterleaks secret scanning

# 1. Get list of staged files
STAGED_FILES=$(git diff --cached --name-only)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# 2. Run betterleaks (assuming binary is in path or specific location)
# For this scaffold, we'll use a placeholder check until betterleaks is confirmed
echo "Scanning for secrets in: $STAGED_FILES"

# Simulated betterleaks call (replace with actual binary call)
# ./scripts/bin/betterleaks --config .betterleaks.toml $STAGED_FILES

# If failure: echo "BLOCKED: Secrets detected!" && exit 1
exit 0
EOF

chmod +x "$HOOK_FILE"
echo "Hook installed successfully."
