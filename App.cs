using Microsoft.Maui.Controls;

namespace MauiNavParentingSelfRefRepro;

public class App : Application
{
	protected override Window CreateWindow(IActivationState? activationState)
		=> new(new NavigationPage(new ProbePage()));
}
