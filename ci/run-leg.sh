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
# The crash report, if the app died, is the second proof of the recursion.
mkdir -p "artifacts/crash-$leg"
# ReportCrash writes the .ips after the process dies; the file is named after the executable (AssemblyName).
for _ in $(seq 1 30); do
  found=$(find "$HOME/Library/Logs/DiagnosticReports" -name 'MauiNavParentingSelfRefRepro*.ips' -newer "$marker" 2>/dev/null)
  [ -n "$found" ] && break
  case "$leg" in bug-crash) sleep 1 ;; *) break ;; esac
done
find "$HOME/Library/Logs/DiagnosticReports" -name 'MauiNavParentingSelfRefRepro*.ips' -newer "$marker" -exec cp {} "artifacts/crash-$leg/" \; 2>/dev/null || true
