#!/usr/bin/env bash
# Runs in the disposable checkout created by the trusted default-branch workflow.
set -euo pipefail
candidate=${1:?missing validated candidate directory}
rsync -a --delete "$candidate/assets/airfields/" assets/airfields/
cp "$candidate"/assets/*.json assets/
cp "$candidate/data/faa.xlsx" data/
git add -- assets/airfields assets/catalog.json assets/airline-profiles.json assets/aircraft-profiles.json assets/sources.json data/faa.xlsx
if git diff --cached --quiet; then
  echo 'Published data is up to date.' >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

# Keep one proposal outstanding. Never overwrite review edits or reopen a rejected snapshot.
open_pr=$(gh pr list --base "$BASE" --state open --json headRefName,url,isCrossRepository --limit 1000 --jq '.[] | select(.isCrossRepository == false and (.headRefName | startswith("automation/data-"))) | .url')
if [[ -n "$open_pr" ]]; then
  echo "A snapshot already awaits review: $open_pr" >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi
tree=$(git write-tree)
branch="automation/data-${tree:0:16}"
previous=$(gh pr list --base "$BASE" --head "$branch" --state all --json url --jq '.[0].url // empty')
if [[ -n "$previous" ]]; then
  echo "This snapshot was already proposed: $previous" >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
gh auth setup-git
git switch -c "$branch"
git commit -m 'Refresh offline aviation data'
if git ls-remote --exit-code --heads origin "refs/heads/$branch"; then
  # Recover a previous run that pushed this branch but failed to open its PR.
  git fetch --no-tags origin "refs/heads/$branch"
  [[ $(git rev-parse 'FETCH_HEAD^{tree}') == "$tree" ]]
else
  git push origin "HEAD:refs/heads/$branch"
fi
gh pr create --base "$BASE" --head "$branch" --title 'Refresh offline aviation data' --body-file "$candidate/review.md" | tee -a "$GITHUB_STEP_SUMMARY"
