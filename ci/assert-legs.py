#!/usr/bin/env python3
"""Asserts every leg's console log; writes the step summary table and results.json. Exit 1 if any leg is wrong."""
import json, os, re, sys

# leg -> (description, [(label, expected, predicate)])
PARENTING_LINE = re.compile(r"^.*NavigationHandlerParentingViewController\S*ChildViewControllerForStatusBarHidden.*$", re.M)
def has(text, needle): return needle in text
def result(text, key):
    m = re.search(r"C09_RESULT .*" + key + r"=(\w+)", text)
    return m.group(1) if m else None

def yn(t, needle): return "found" if needle in t else "not found"
def parenting_frame(t):
    m = PARENTING_LINE.search(t)
    return m.group(0).strip()[:200] if m else "none"

# leg -> (description, checks(text) -> [(label, expected, observed, passed)])
legs = {
    "bug-self-return": ("page handler disconnected, UIKit queries the parenting VC", lambda t: [
        ("started", "C09_START present", yn(t, "C09_START mode=self-bug"), has(t, "C09_START mode=self-bug")),
        ("ChildViewControllerForStatusBarHidden returns itself", "True", f"statusBarHiddenReturnsSelf={result(t, 'statusBarHiddenReturnsSelf')}", result(t, "statusBarHiddenReturnsSelf") == "True"),
        ("ChildViewControllerForHomeIndicatorAutoHidden returns itself", "True", f"homeIndicatorReturnsSelf={result(t, 'homeIndicatorReturnsSelf')}", result(t, "homeIndicatorReturnsSelf") == "True"),
    ]),
    "control-self-return": ("page handler connected", lambda t: [
        ("started", "C09_START present", yn(t, "C09_START mode=self-control"), has(t, "C09_START mode=self-control")),
        ("ChildViewControllerForStatusBarHidden returns itself", "False", f"statusBarHiddenReturnsSelf={result(t, 'statusBarHiddenReturnsSelf')}", result(t, "statusBarHiddenReturnsSelf") == "False"),
        ("ChildViewControllerForHomeIndicatorAutoHidden returns itself", "False", f"homeIndicatorReturnsSelf={result(t, 'homeIndicatorReturnsSelf')}", result(t, "homeIndicatorReturnsSelf") == "False"),
    ]),
    "bug-crash": ("DisconnectHandlers() then replace the root view controller", lambda t: [
        ("trigger ran", "C09_TRIGGER_BEGIN present", "C09_TRIGGER_BEGIN " + yn(t, "C09_TRIGGER_BEGIN disconnectBeforeSwap=True"), has(t, "C09_TRIGGER_BEGIN disconnectBeforeSwap=True")),
        ("app did not survive", "no C09_SURVIVED", "C09_SURVIVED " + yn(t, "C09_SURVIVED"), not has(t, "C09_SURVIVED")),
        ("native stack overflow", "'Stack overflow' in the log", "'Stack overflow' " + yn(t, "Stack overflow"), "Stack overflow" in t),
        ("recursion is the parenting VC callback", "a line matching NavigationHandlerParentingViewController...ChildViewControllerForStatusBarHidden", parenting_frame(t), bool(PARENTING_LINE.search(t))),
    ]),
    "control-crash": ("replace the root view controller, then DisconnectHandlers()", lambda t: [
        ("trigger ran", "C09_TRIGGER_BEGIN present", "C09_TRIGGER_BEGIN " + yn(t, "C09_TRIGGER_BEGIN disconnectBeforeSwap=False"), has(t, "C09_TRIGGER_BEGIN disconnectBeforeSwap=False")),
        ("app survived", "C09_SURVIVED present", "C09_SURVIVED " + yn(t, "C09_SURVIVED"), has(t, "C09_SURVIVED")),
        ("no stack overflow", "'Stack overflow' absent", "'Stack overflow' " + yn(t, "Stack overflow"), "Stack overflow" not in t),
    ]),
}

def esc(v): return str(v).replace("|", "\\|")

os.makedirs("artifacts", exist_ok=True)
rows, out, starts, ok = [], {}, [], True
for leg, (desc, checks) in legs.items():
    path = f"artifacts/console-{leg}.txt"
    text = open(path, errors="replace").read() if os.path.exists(path) else ""
    if not text.strip():
        rows.append(f"| {leg} | log | log present and non-empty | missing or empty | FAIL |")
        out[leg] = {"passed": False, "reason": "no log"}; ok = False; continue
    results = checks(text)
    for label, expected, observed, passed in results:
        rows.append(f"| {leg} | {esc(label)} | {esc(expected)} | {esc(observed)} | {'PASS' if passed else 'FAIL'} |")
        ok &= bool(passed)
    start = next((l.strip() for l in text.splitlines() if "C09_START" in l), "no C09_START line")
    starts.append(f"- `{leg}`: `{start}`")
    out[leg] = {"description": desc, "passed": all(r[3] for r in results),
                "observed": {label: observed for label, _, observed, _ in results},
                "start": start}

def leg_ok(name): return out.get(name, {}).get("passed", False)
bug = all(leg_ok(n) for n in ("bug-self-return", "bug-crash"))
control = all(leg_ok(n) for n in ("control-self-return", "control-crash"))
headline = (f"**Bug reproduced: {'yes' if bug else 'no'} (bug-self-return, bug-crash). "
            f"Control clean: {'yes' if control else 'no'} (control-self-return, control-crash).**")
summary = ("### C09 results\n\n" + headline + "\n\n| Leg | Check | Expected | Observed | Result |\n|---|---|---|---|---|\n"
           + "\n".join(rows) + "\n\n" + "\n".join(starts) + "\n")
print(summary)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(summary)
out["bug_reproduced"] = bug
out["control_clean"] = control
json.dump(out, open("artifacts/results.json", "w"), indent=2)
sys.exit(0 if ok else 1)
