#!/usr/bin/env python3
"""Asserts every leg's console log; writes the step summary table and results.json. Exit 1 if any leg is wrong."""
import json, os, re, sys

# leg -> (description, [(label, expected, predicate)])
def has(text, needle): return needle in text
def result(text, key):
    m = re.search(r"C09_RESULT .*" + key + r"=(\w+)", text)
    return m.group(1) if m else None

legs = {
    "bug-self-return": ("page handler disconnected, UIKit queries the parenting VC", lambda t: [
        ("started", "C09_START present", has(t, "C09_START mode=self-bug")),
        ("ChildViewControllerForStatusBarHidden returns itself", "True", result(t, "statusBarHiddenReturnsSelf") == "True"),
        ("ChildViewControllerForHomeIndicatorAutoHidden returns itself", "True", result(t, "homeIndicatorReturnsSelf") == "True"),
    ]),
    "control-self-return": ("page handler connected", lambda t: [
        ("started", "C09_START present", has(t, "C09_START mode=self-control")),
        ("ChildViewControllerForStatusBarHidden returns itself", "False", result(t, "statusBarHiddenReturnsSelf") == "False"),
        ("ChildViewControllerForHomeIndicatorAutoHidden returns itself", "False", result(t, "homeIndicatorReturnsSelf") == "False"),
    ]),
    "bug-crash": ("DisconnectHandlers() then replace the root view controller", lambda t: [
        ("trigger ran", "C09_TRIGGER_BEGIN present", has(t, "C09_TRIGGER_BEGIN disconnectBeforeSwap=True")),
        ("app did not survive", "no C09_SURVIVED", not has(t, "C09_SURVIVED")),
        ("native stack overflow", "'Stack overflow' in the log", "Stack overflow" in t),
        ("recursion is the parenting VC callback", "ChildViewControllerForStatusBarHidden in the log", "ChildViewControllerForStatusBarHidden" in t),
    ]),
    "control-crash": ("replace the root view controller, then DisconnectHandlers()", lambda t: [
        ("trigger ran", "C09_TRIGGER_BEGIN present", has(t, "C09_TRIGGER_BEGIN disconnectBeforeSwap=False")),
        ("app survived", "C09_SURVIVED present", has(t, "C09_SURVIVED")),
        ("no stack overflow", "'Stack overflow' absent", "Stack overflow" not in t),
    ]),
}

os.makedirs("artifacts", exist_ok=True)
rows, out, ok = [], {}, True
for leg, (desc, checks) in legs.items():
    path = f"artifacts/console-{leg}.txt"
    text = open(path, errors="replace").read() if os.path.exists(path) else ""
    if not text.strip():
        rows.append(f"| {leg} | log missing or empty | n/a | FAIL |")
        out[leg] = {"passed": False, "reason": "no log"}; ok = False; continue
    results = checks(text)
    for label, expected, passed in results:
        rows.append(f"| {leg} | {label} | expected: {expected} | {'PASS' if passed else 'FAIL'} |")
        ok &= bool(passed)
    out[leg] = {"description": desc, "passed": all(p for _, _, p in results)}

summary = "### C09 results\n\n| Leg | Check | Expectation | Result |\n|---|---|---|---|\n" + "\n".join(rows) + "\n"
print(summary)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(summary)
json.dump(out, open("artifacts/results.json", "w"), indent=2)
sys.exit(0 if ok else 1)
