#!/bin/sh
# Reproduce quirks 1, 2, 3 and 5 from index.html with the script's own logic, without root
# and without touching the system. Run with any sh: `sh verify_quirks.sh`, `bash verify_quirks.sh`.
set -u
available() { command -v $1 >/dev/null; }
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1: $2"; else echo "FAIL $1: got '$2', expected '$3'"; fail=1; fi; }

# 1. trap replaces, not appends: the cleanup handler from L20 never runs after L193
check "q1 trap" "$( (trap 'echo cleanup' EXIT; trap 'echo install_success' EXIT; true) )" "install_success"

# 2. L393-L402: after a for loop without break, the variable keeps its last value
PACKAGE_MANAGER=
for PACKAGE_MANAGER in no_such_dnf no_such_yum no_such_apt; do
    if available $PACKAGE_MANAGER; then break; fi
done
check "q2 empty check fires" "$([ -z "$PACKAGE_MANAGER" ] && echo yes || echo no)" "no"

# 3. L159-L176: PATH without /usr/local/bin or /usr/bin falls back to /bin and triggers the ln
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
for BINDIR in /usr/local/bin /usr/bin /bin; do echo /opt/x | grep -q $BINDIR && break || continue; done
D=$(dirname $BINDIR)
check "q3 BINDIR" "$BINDIR" "/bin"
check "q3 link taken" "$([ "$D/bin/ollama" != "$BINDIR/ollama" ] && echo yes || echo no)" "yes"
mkdir -p "$T/bin" && echo real > "$T/bin/ollama" && ln -sf "$T//ollama" "$T/bin/ollama"
check "q3 binary replaced by dangling link" "$([ -L "$T/bin/ollama" ] && [ ! -e "$T/bin/ollama" ] && echo yes || echo no)" "yes"

# 5. L407: Rocky major version by first character
check "q5 rocky 10.0" "$(echo 10.0 | cut -c1)" "1"
exit $fail
