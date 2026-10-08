#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
/usr/bin/time -p pwd
PORT="${PORT:-3000}"
PROJECT_ROOT="$(pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
/usr/bin/time -p test -f "$DIST_DIR/index.html"
if /usr/bin/time -p test -f "$PROJECT_ROOT/package.json"; then
  /usr/bin/time -p npm install --no-audit --no-fund
  /usr/bin/time -p npm run build
fi
/usr/bin/time -p mkdir -p "${OPENCODE_WEB_DIR:?OPENCODE_WEB_DIR is not set}"
/usr/bin/time -p python3 -c "import json,os; root=os.path.abspath('.'); dist=os.path.join(root,'dist'); web=os.environ['OPENCODE_WEB_DIR']; open(os.path.join(web,'deployment-output.json'),'w').write(json.dumps({'project':root,'directory':dist}))"
/usr/bin/time -p cat "$OPENCODE_WEB_DIR/deployment-output.json"
/usr/bin/time -p python3 -m http.server "$PORT" --directory "$DIST_DIR"
