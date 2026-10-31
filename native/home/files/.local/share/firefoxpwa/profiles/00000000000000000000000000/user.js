// Shared PWA appearance only. Keep device/account state in prefs.js.
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("layout.css.prefers-color-scheme.content-override", 0);
user_pref("browser.display.background_color", "#191724");
user_pref("browser.display.background_color.dark", "#191724");
user_pref("browser.display.foreground_color", "#e0def4");
user_pref("browser.display.foreground_color.dark", "#e0def4");
// Site manifests (including Gmail) can otherwise restore a white launch canvas.
user_pref("firefoxpwa.sitesSetBackgroundColor", false);
// The early navigator:blank window is shown before user styles can apply.
// Wait for the real, palette-styled browser window instead.
user_pref("browser.startup.blankWindow", false);
