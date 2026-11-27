#!/usr/bin/env bash
# usage: run-leg.sh <leg-name> <mode>; the booted simulator's UDID is in $UDID.
set -uo pipefail
leg="$1"; mode="$2"
mkdir -p artifacts
marker="artifacts/.launch-$leg"; touch "$marker"
app=$(ls -d bin/Release/net11.0-ios/iossimulator-arm64/*.app | head -1)
xcrun simctl install "$UDID" "$app"
# macOS has no timeout command; perl's alarm survives exec.
perl -e 'alarm shift; exec @ARGV' 120 \
  xcrun simctl launch --console-pty --terminate-running-process "$UDID" com.example.mauinavparentingselfref --mode="$mode" 2>&1 | tee "artifacts/console-$leg.txt" || true
# simctl prints "<bundle id>: <pid>" on launch. Reports are matched by pid because ReportCrash can write
# one over a minute after the crash, when the next leg is already running.
pid=$(tr -d '\r' < "artifacts/console-$leg.txt" | sed -n 's/^com\.example\.mauinavparentingselfref: \([0-9][0-9]*\)$/\1/p' | head -1)
mkdir -p "artifacts/crash-$leg"
echo "$pid" > "artifacts/pid-$leg.txt"
find_reports() {
  [ -n "$pid" ] || return 0
  grep -lE "\"pid\"[[:space:]]*:[[:space:]]*$pid[,}[:space:]]" "$HOME"/Library/Logs/DiagnosticReports/MauiNavParentingSelfRefRepro*.ips 2>/dev/null || true
}
attempts=1
[ "$leg" = bug-crash ] && attempts=300
for _ in $(seq 1 "$attempts"); do
  found=$(find_reports)
  [ -n "$found" ] && break
  [ "$attempts" -gt 1 ] && sleep 1
done
for f in $found; do cp "$f" "artifacts/crash-$leg/"; done
