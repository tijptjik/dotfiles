// The scrolling layout expands a window without setting Zen's maximized state.
function update(win) {
  const screen = win.screen;
  const fullWidth = win.outerWidth >= screen.availWidth &&
    win.outerHeight >= screen.availHeight;
  win.document.documentElement.toggleAttribute("dotjik-full-width", fullWidth);
}

function install(win) {
  if (!win.gBrowser || win.__dotjikFullWidthChrome) return;
  win.__dotjikFullWidthChrome = true;
  win.addEventListener("resize", () => update(win));
  win.addEventListener("sizemodechange", () => update(win));
  update(win);
}

Services.obs.addObserver({ observe: install }, "browser-delayed-startup-finished");
for (const win of Services.wm.getEnumerator("navigator:browser")) {
  if (win.gBrowserInit?.delayedStartupFinished) install(win);
}
