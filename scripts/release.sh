#!/usr/bin/env bash
# scripts/release.sh — local release helper
# Usage: bash scripts/release.sh 0.2.0a2
# This bumps version in pyproject.toml + __init__.py, commits, and tags.

set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>  e.g. $0 0.2.0a2"
  exit 1
fi

echo "Bumping to $VERSION ..."

# Update pyproject.toml
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Update __init__.py
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" \
  sdk/python/agentability/__init__.py

# Verify
echo "pyproject.toml: $(grep '^version' pyproject.toml)"
echo "__init__.py:    $(grep '__version__' sdk/python/agentability/__init__.py)"

# Run quality gate
make lint && make type-check && make test

# Commit + tag
git add pyproject.toml sdk/python/agentability/__init__.py
git commit -m "chore: bump version to $VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION"

echo ""
echo "Done. Run: git push origin main --tags"
echo "The release workflow will publish to PyPI automatically."
