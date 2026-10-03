#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

LOGIN_HTML="$REPO_DIR/router/routercloud/webui/metro/login.html"
LOGIN_JS="$REPO_DIR/router/routercloud/webui/metro/login.js"

for file in "$LOGIN_HTML" "$LOGIN_JS"; do
    [ -s "$file" ] || {
        echo "FAIL: missing RouterCloud login asset: $file" >&2
        exit 1
    }
done

grep -F 'ROUTERCLOUD_EMAIL_LOGIN_UI_V1' "$LOGIN_HTML" >/dev/null
grep -F 'ROUTERCLOUD_EMAIL_LOGIN_UI_V1' "$LOGIN_JS" >/dev/null
grep -F 'name="username"' "$LOGIN_HTML" >/dev/null
grep -F 'placeholder="Nazwa użytkownika lub e-mail"' "$LOGIN_HTML" >/dev/null
grep -F 'autocomplete="username"' "$LOGIN_HTML" >/dev/null
grep -F '"Nieprawidłowy login lub hasło."' "$LOGIN_JS" >/dev/null

if grep -F '"Nieprawidłowa nazwa użytkownika lub hasło."' "$LOGIN_JS" >/dev/null; then
    echo "FAIL: stale username-only login error remains" >&2
    exit 1
fi

echo "PASS: RouterCloud email-login UI static checks"
