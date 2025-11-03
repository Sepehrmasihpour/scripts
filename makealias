cat >/tmp/makealias <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: makealias '<command>' <alias_name>"
  echo "Example: makealias 'git status -sb' gst"
  exit 64
fi

cmd="$1"
alias_name="$2"

# simple validation for alias names
if ! [[ "$alias_name" =~ ^[a-zA-Z_][a-zA-Z0-9_+-]*$ ]]; then
  echo "Error: alias name '$alias_name' is invalid (use letters, digits, _, +, -; not starting with a digit)."
  exit 65
fi

aliases_file="$HOME/.bash_aliases"
bashrc="$HOME/.bashrc"

# ensure .bash_aliases is sourced by .bashrc (Debian often has this, but let's be sure)
if ! grep -qE '(^|/)\.bash_aliases' "$bashrc" 2>/dev/null; then
  printf '\n# Load user aliases\nif [ -f ~/.bash_aliases ]; then . ~/.bash_aliases; fi\n' >> "$bashrc"
fi

# escape single quotes inside the command so it can live inside single quotes
escaped_cmd=${cmd//\'/\'\\\'\'}
line="alias $alias_name='$escaped_cmd'"

mkdir -p "$(dirname "$aliases_file")"
touch "$aliases_file"

if grep -qE "^alias[[:space:]]+$alias_name=" "$aliases_file"; then
  # update existing alias
  sed -i.bak -E "s|^alias[[:space:]]+$alias_name=.*|$line|" "$aliases_file"
  action="updated"
else
  echo "$line" >> "$aliases_file"
  action="added"
fi

echo "Alias '$alias_name' -> $cmd $action in $aliases_file."
echo "Open a new shell, or load it now with:  source \"$bashrc\""
EOF

# install system-wide so you can call it from anywhere
sudo install -m 0755 /tmp/makealias /usr/local/bin/makealias
