# Waybar workspace sorting

`waybar-numeric-workspace-sort.patch` fixes `ext/workspaces` name sorting when
hidden special workspaces coexist with numbered workspaces. Numeric names sort
first using Waybar's existing numeric comparison; other names sort lexically
afterward. Visibility and workspace activation are unchanged.

Applied to `/home/io/.local/src/waybar-lua` at upstream revision
`acb295bc188fb6043016e386358c3737063685e5`. The desktop launches
`/home/io/.local/bin/waybar`.

After a source update, inspect the checkout before applying the patch:

```sh
git -C /home/io/.local/src/waybar-lua apply --check /home/io/.local/share/chezmoi/docs/patches/waybar-numeric-workspace-sort.patch
git -C /home/io/.local/src/waybar-lua apply /home/io/.local/share/chezmoi/docs/patches/waybar-numeric-workspace-sort.patch
ninja -C /home/io/.local/src/waybar-lua/build -j2
```

Reinstall the resulting binary and restart Waybar after a successful build.
The patch is retained here for reapplication; automatic build scripts do not
apply it. Removing `sort-by-name` from the configuration does not disable name
sorting because it defaults to true.

Validation: the actual patched `sort_workspaces()` function passed all 120
permutations of `1`, `2`, `10`, `special:chat`, and `special:codex` in a standalone
C++ harness, always producing that order.
