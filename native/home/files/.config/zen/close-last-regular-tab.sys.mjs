// Close the active Zen window only after a user closes its last regular tab.
// Pinned tabs, Essentials, and Zen's internal empty tab do not count.
// Loaded for every profile by Dotjik's /opt/zen/config.js autoconfig hook.

function isRegular(tab) {
  return !tab.pinned &&
    !tab.hasAttribute("zen-essential") &&
    !tab.hasAttribute("zen-empty-tab") &&
    !tab.hasAttribute("glance-id");
}

function install(win) {
  if (!win.gBrowser || !win.gZenWorkspaces || win.__closeLastRegularTab) return;
  win.__closeLastRegularTab = true;
  win.gBrowser.tabContainer.addEventListener("TabClose", event => {
    // Startup cleanup and window sync also emit TabClose. Zen carries the
    // explicit user-action marker from keyboard, close-button and menu handlers.
    if (event.detail?.metricsContext?.isUserTriggered !== true) return;
    // Zen mirrors tab removals into other windows. Only close the active one.
    if (Services.focus.activeWindow !== win || win.closed || win.closing ||
        event.detail?.adoptedBy || !isRegular(event.target)) return;
    const removed = event.target;
    const hasRegularTabs = () => Array.from(win.gBrowser.tabs).some(tab =>
      tab !== removed && !tab.closing && isRegular(tab));
    // Decide at the user action, not after unrelated cleanup empties the window.
    if (hasRegularTabs()) return;
    win.setTimeout(() => {
      if (win.closed || win.closing) return;
      // Include other workspaces and collapsed groups: never discard regular tabs.
      if (!hasRegularTabs()) {
        // Use the normal close command, retaining unload prompts and session state.
        win.document.getElementById("cmd_closeWindow")?.doCommand();
      }
    }, 0);
  });
}

const observer = { observe: install };
Services.obs.addObserver(observer, "browser-delayed-startup-finished");
for (const win of Services.wm.getEnumerator("navigator:browser")) {
  if (win.gBrowserInit?.delayedStartupFinished) install(win);
}
