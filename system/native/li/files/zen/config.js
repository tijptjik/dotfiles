// Dotjik Zen autoconfig. The first line is intentionally a comment.
// Require a deliberate edge hover before revealing compact-mode panels.
pref("zen.view.compact.hover-hack-delay", 300);

// Load managed behavior before optional legacy per-profile userChromeJS.
try {
  const directories = Cc["@mozilla.org/file/directory_service;1"].getService(Ci.nsIProperties);
  const script = directories.get("Home", Ci.nsIFile);
  for (const part of [".config", "zen", "close-last-regular-tab.sys.mjs"]) script.append(part);
  if (script.exists()) {
    const io = Cc["@mozilla.org/network/io-service;1"].getService(Ci.nsIIOService);
    const resources = io.getProtocolHandler("resource").QueryInterface(Ci.nsIResProtocolHandler);
    resources.setSubstitution("dotjik-zen", io.newFileURI(script.parent));
    ChromeUtils.importESModule("resource://dotjik-zen/close-last-regular-tab.sys.mjs");
  }
} catch (error) {
  // A missing/broken customization must never prevent the browser from opening.
  Components.utils.reportError(error);
}

// Preserve existing userChromeJS installations without requiring one.
try {
  const manifest = Cc["@mozilla.org/file/directory_service;1"]
    .getService(Ci.nsIProperties).get("UChrm", Ci.nsIFile);
  manifest.append("utils");
  manifest.append("chrome.manifest");
  if (manifest.exists()) {
    Components.manager.QueryInterface(Ci.nsIComponentRegistrar).autoRegister(manifest);
    ChromeUtils.importESModule("chrome://userchromejs/content/boot.sys.mjs");
  }
} catch (error) {
  Components.utils.reportError(error);
}
