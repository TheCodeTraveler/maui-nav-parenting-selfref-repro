using UIKit;

namespace MauiNavParentingSelfRefRepro;

public static class Program
{
	static void Main(string[] args) => UIApplication.Main(args, null, typeof(AppDelegate));
}

[Foundation.Register(nameof(AppDelegate))]
public class AppDelegate : Microsoft.Maui.MauiUIApplicationDelegate
{
	protected override Microsoft.Maui.Hosting.MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}

// Named by UISceneDelegateClassName in Info.plist; the iOS 27 SDK terminates apps that do not adopt the UIScene life cycle.
[Foundation.Register(nameof(SceneDelegate))]
public class SceneDelegate : Microsoft.Maui.MauiUISceneDelegate
{
}
