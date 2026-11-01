#!/bin/sh
# Is this machine ready for the packs? Checks what the scripts import and the tools the checks call:
# Python 3.10 or later, the packages in requirements.txt, the Chromium that prints a page, and pdftotext.
#
#   sh portable-pack/doctor.sh          say what is in place and what is missing
#   sh portable-pack/doctor.sh --fix    make .venv beside the clone if there is none, install the packages and
#                                       Chromium into it; print the one system command still needed
#
# It uses the virtual environment you are in, or .venv at the top of the clone. It never runs sudo: a line
# that needs it is printed for you to run. Then start your agent from a shell where that environment is active.
PACK=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$PACK")
FIX=no
[ "$1" = "--fix" ] && FIX=yes
MISSING=0
os=$(uname -s)

say() { printf '%-9s %s\n' "$1" "$2"; }

if [ -n "$VIRTUAL_ENV" ]; then
  VENV=$VIRTUAL_ENV
else
  VENV=$ROOT/.venv
fi
PY=$VENV/bin/python3

# 1. Python
base=$(command -v python3)
if [ -z "$base" ]; then
  say missing "python3: install Python 3.10 or later (python.org, brew install python, apt install python3)"
  exit 1
fi
if ! "$base" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  say missing "Python 3.10 or later: python3 is $("$base" -c 'import platform; print(platform.python_version())')"
  exit 1
fi
if [ ! -x "$PY" ]; then
  if [ "$FIX" = yes ]; then
    "$base" -m venv "$VENV" || { say missing "a virtual environment: on Debian and Ubuntu, sudo apt install python3-venv"; exit 1; }
    say made "$VENV"
  else
    say missing "a virtual environment at $VENV (python3 -m venv .venv, or run with --fix)"
    MISSING=$((MISSING + 1))
    PY=$base
  fi
fi
say ok "Python $("$PY" -c 'import platform; print(platform.python_version())') at $PY"

# 2. The packages the scripts import (module name: package name)
mods="docx:python-docx pptx:python-pptx openpyxl:openpyxl playwright:playwright pypdf:pypdf numpy:numpy PIL:Pillow pypdfium2:pypdfium2"
absent=""
for pair in $mods; do
  "$PY" -c "import ${pair%%:*}" 2>/dev/null || absent="$absent ${pair#*:}"
done
if [ -n "$absent" ] && [ "$FIX" = yes ]; then
  "$PY" -m pip install --quiet --disable-pip-version-check -r "$PACK/requirements.txt" && absent=""
fi
if [ -z "$absent" ]; then
  say ok "the Python packages in requirements.txt"
else
  say missing "Python packages:$absent (pip install -r portable-pack/requirements.txt, or run with --fix)"
  MISSING=$((MISSING + 1))
fi

# 3. Chromium, which prints an invoice or a trade document to PDF: launched once, so missing libraries show too
launch() {
  "$PY" - <<'EOF' 2>&1
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.launch().close()
EOF
}
if "$PY" -c "import playwright" 2>/dev/null; then
  out=$(launch); rc=$?
  if [ $rc -ne 0 ] && [ "$FIX" = yes ] && printf '%s' "$out" | grep -q "Executable doesn't exist"; then
    "$PY" -m playwright install chromium >/dev/null && { out=$(launch); rc=$?; }
  fi
  if [ $rc -eq 0 ]; then
    say ok "Chromium prints a page"
  elif printf '%s' "$out" | grep -q "Executable doesn't exist"; then
    say missing "Chromium: playwright install chromium (or run with --fix)"
    MISSING=$((MISSING + 1))
  else
    say missing "the libraries Chromium needs: sudo $VENV/bin/playwright install-deps chromium"
    MISSING=$((MISSING + 1))
  fi
else
  say missing "Chromium: comes after the Python packages"
  MISSING=$((MISSING + 1))
fi

# 4. pdftotext, which the checks read every PDF with
if command -v pdftotext >/dev/null 2>&1; then
  say ok "pdftotext"
elif [ "$os" = Darwin ] && [ "$FIX" = yes ] && command -v brew >/dev/null 2>&1 && brew install --quiet poppler >/dev/null; then
  say ok "pdftotext (brew install poppler)"
elif [ "$os" = Darwin ]; then
  say missing "pdftotext: brew install poppler"
  MISSING=$((MISSING + 1))
else
  say missing "pdftotext: sudo apt install poppler-utils (dnf install poppler-utils on Fedora)"
  MISSING=$((MISSING + 1))
fi

# 5. Only some packs need these
command -v soffice >/dev/null 2>&1 || command -v libreoffice >/dev/null 2>&1 \
  && say ok "LibreOffice" || say optional "LibreOffice, for spreadsheets and the deck's page measures"
command -v tectonic >/dev/null 2>&1 && say ok "tectonic" || say optional "tectonic, for the academic paper"
command -v ffmpeg >/dev/null 2>&1 && say ok "ffmpeg" || say optional "ffmpeg, for the poster"

echo
if [ "$MISSING" -eq 0 ]; then
  echo "Ready. Start your agent from a shell with this environment active: . $VENV/bin/activate"
else
  echo "$MISSING to fix, above. Then run this again."
  exit 1
fi
