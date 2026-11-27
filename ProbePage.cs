using Foundation;
using Microsoft.Maui;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Platform;
using UIKit;

namespace MauiNavParentingSelfRefRepro;

public class ProbePage : ContentPage
{
	const string modeSelfBug = "self-bug";
	const string modeSelfControl = "self-control";
	const string modeCrashBug = "crash-bug";
	const string modeCrashControl = "crash-control";

	// The navigation stack must finish its first layout pass before handlers are disconnected.
	static readonly TimeSpan initialNavigationSettleTime = TimeSpan.FromMilliseconds(1500);

	// UIKit queries the status bar child on a later layout pass, so the process must outlive the trigger.
	static readonly TimeSpan lateStatusBarWalkWindow = TimeSpan.FromSeconds(3);

	bool hasStarted;

	public ProbePage() => Content = new Label { Text = "Running, see the console output" };

	protected override async void OnAppearing()
	{
		base.OnAppearing();
		if (hasStarted)
		{
			return;
		}

		hasStarted = true;
		var mode = GetModeFromLaunchArguments();
		Console.WriteLine($"C09_START mode={mode} runtime={System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription} os={UIDevice.CurrentDevice.SystemVersion}");
		await Task.Delay(initialNavigationSettleTime);

		switch (mode)
		{
			case modeSelfBug:
				ReportSelfReturns(disconnectPageHandler: true, mode);
				break;
			case modeSelfControl:
				ReportSelfReturns(disconnectPageHandler: false, mode);
				break;
			case modeCrashBug:
				await RunRootSwapAsync(disconnectBeforeSwap: true);
				break;
			case modeCrashControl:
				await RunRootSwapAsync(disconnectBeforeSwap: false);
				break;
			default:
				Console.WriteLine($"C09_ERROR unknown mode '{mode}'");
				Environment.Exit(2);
				break;
		}

		Console.WriteLine("C09_DONE");
		Environment.Exit(0);
	}

	static string GetModeFromLaunchArguments()
		=> NSProcessInfo.ProcessInfo.Arguments.FirstOrDefault(argument => argument.StartsWith("--mode=", StringComparison.Ordinal))?["--mode=".Length..] ?? modeSelfBug;

	UINavigationController GetNavigationController()
		=> (UINavigationController)((IPlatformViewHandler)((NavigationPage)Parent).Handler!).ViewController!;

	void ReportSelfReturns(bool disconnectPageHandler, string mode)
	{
		var navigationController = GetNavigationController();
		var parentingViewController = navigationController.TopViewController!;
		Console.WriteLine($"C09_INFO parenting={parentingViewController.GetType().FullName} nav={navigationController.GetType().FullName}");

		if (disconnectPageHandler)
		{
			this.DisconnectHandlers();
		}

		var statusBarHiddenChild = parentingViewController.ChildViewControllerForStatusBarHidden();
		var homeIndicatorChild = parentingViewController.ChildViewControllerForHomeIndicatorAutoHidden;
		var statusBarReturnsSelf = ReferenceEquals(statusBarHiddenChild, parentingViewController);
		var homeIndicatorReturnsSelf = ReferenceEquals(homeIndicatorChild, parentingViewController);
		Console.WriteLine($"C09_RESULT mode={mode} statusBarHiddenReturnsSelf={statusBarReturnsSelf} homeIndicatorReturnsSelf={homeIndicatorReturnsSelf}");
	}

	async Task RunRootSwapAsync(bool disconnectBeforeSwap)
	{
		var navigationPage = (NavigationPage)Parent;
		var uiWindow = Window.Handler!.PlatformView as UIWindow ?? throw new InvalidOperationException("No UIWindow");

		Console.WriteLine($"C09_TRIGGER_BEGIN disconnectBeforeSwap={disconnectBeforeSwap}");
		if (disconnectBeforeSwap)
		{
			navigationPage.DisconnectHandlers();
			uiWindow.RootViewController = null;
		}
		else
		{
			uiWindow.RootViewController = null;
			navigationPage.DisconnectHandlers();
		}

		await Task.Delay(lateStatusBarWalkWindow);
		Console.WriteLine("C09_SURVIVED");
	}
}
