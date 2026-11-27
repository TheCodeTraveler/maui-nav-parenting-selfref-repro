# maui-nav-parenting-selfref-repro

On iOS, `NavigationHandlerParentingViewController` (the view controller `NavigationViewHandler` puts in every `NavigationPage`) returns **itself** from `ChildViewControllerForStatusBarHidden()` and `ChildViewControllerForHomeIndicatorAutoHidden` once its page's handler is disconnected. UIKit expects a child view controller or `nil`, so it asks the same controller again until the native stack overflows.

## Reproduce

Needs macOS with Xcode 27 and the MAUI iOS workload (`dotnet workload install maui-ios --version 11.0.100.1`):

```sh
dotnet build -c Release
xcrun simctl install booted bin/Release/net11.0-ios/iossimulator-arm64/*.app
xcrun simctl launch --console-pty booted com.example.mauinavparentingselfref --mode=self-bug
```

Modes: `self-bug`, `self-control`, `crash-bug`, `crash-control`.

## Observed vs expected

| Mode | Observed (11.0.10) | Expected |
|---|---|---|
| `self-bug` | `statusBarHiddenReturnsSelf=True homeIndicatorReturnsSelf=True` | `False` for both |
| `crash-bug` | `Stack overflow` in `ChildViewControllerForStatusBarHidden` in `NavigationHandlerParentingViewController` under `UIWindow.set_RootViewController(null)`; no `C09_SURVIVED` | app survives |

## Versions

`Microsoft.Maui.Controls` 11.0.10, SDK 11.0.100 (`global.json`), iOS workload 11.0.100.1, Xcode 27.2, newest iOS simulator on the `xcode-27` runner. The code is identical on `main`.

## Legs (one job, `.github/workflows/repro.yml`)

| Leg | Trigger | Passes when |
|---|---|---|
| `bug-self-return` | `DisconnectHandlers()` on the page, then ask the parenting VC for its status-bar and home-indicator children | both return the parenting VC itself |
| `control-self-return` | same, without the disconnect | both return the page's VC (not itself) |
| `bug-crash` | `NavigationPage.DisconnectHandlers()`, then set `UIWindow.RootViewController = null` | `C09_TRIGGER_BEGIN`, no `C09_SURVIVED`, `Stack overflow`, and a log line matching `NavigationHandlerParentingViewController\S*ChildViewControllerForStatusBarHidden` (shown in the summary) |
| `control-crash` | `RootViewController = null` first, then `DisconnectHandlers()` (the order MAUI uses itself) | `C09_SURVIVED`, no `Stack overflow` |

Each leg fails when its log is missing or its marker line is absent. The workflow is green only when every bug leg shows the bug and every control leg is clean. The job summary opens with one line (bug reproduced yes/no, control clean yes/no), then lists expected vs observed per leg and each leg's `C09_START` line; logs and crash reports are uploaded as artifacts.

There is no fix leg: the view controller is `internal sealed` and created inside `NavigationViewHandler`, so user code cannot replace or subclass it. The workaround is the control order: replace the window's root before disconnecting a `NavigationPage`.

CI: (run link added after the first run)

Upstream issue: (to be filed)

## Root cause and fix

`src/Controls/src/Core/Platform/iOS/NavigationViewHandlerToolbarHelper.cs`:

```csharp
public override UIViewController ChildViewControllerForHomeIndicatorAutoHidden =>
    (Child?.Handler as IPlatformViewHandler)?.ViewController ?? this;

public override UIViewController ChildViewControllerForStatusBarHidden() =>
    (Child?.Handler as IPlatformViewHandler)?.ViewController ?? this;
```

`Child` or its handler is null after the page's handler disconnects, or after `NavigationViewHandler.OnDisconnectHandler` disposes the parenting VC. `ChildViewControllerForStatusBarStyle` right below already falls back to `base`. Recommended fix: use `?? base.ChildViewControllerForStatusBarHidden()` and `?? base.ChildViewControllerForHomeIndicatorAutoHidden`. Introduced by dotnet/maui#36109 (the legacy `NavigationRenderer` never returned itself).
