using Microsoft.Maui.Hosting;

namespace MauiNavParentingSelfRefRepro;

public static class MauiProgram
{
	public static MauiApp CreateMauiApp() => MauiApp.CreateBuilder().UseMauiApp<App>().Build();
}
