# Extracting archived Sonarr releases

Sonarr does not extract release archives as part of import. Configure the
download client instead, so the extracted video is present before Sonarr's
completed-download handling scans the release. This repository installs
`~/.config/transmission/extract.fish` and mounts it into the LinuxServer
Transmission container as `/usr/local/bin/extract-sonarr-archives`.

The hook supports RAR (including `part01.rar` sets), ZIP, 7z (including
`.7z.001` sets), and tar archives. It extracts into the release directory,
recursively searches that directory, and never deletes the archive volumes;
that preserves Transmission seeding. Password-protected or incomplete archives
are logged as failures and left untouched.

## Enable the Transmission completion hook

1. Apply this repository so that the hook file and compose mount exist:

   ```bash
   chezmoi apply
   ```

2. Stop Transmission before editing its live settings file. In this compose
   configuration it is at
   `/mnt/storage/meta/appData/transmission/settings.json`.
   Add or change these keys (the path is inside the container):

   ```json
   "script-torrent-done-enabled": true,
   "script-torrent-done-filename": "/usr/local/bin/extract-sonarr-archives",
   "script-torrent-done-seeding-enabled": false
   ```

   For example:

   ```bash
   docker compose stop transmission
   $EDITOR /mnt/storage/meta/appData/transmission/settings.json
   docker compose up -d transmission
   ```

   Transmission rewrites `settings.json` on shutdown, hence the stop-before-
   edit order. If those keys already exist, change their values instead of
   adding duplicate JSON keys.

3. Start Transmission from the directory containing the rendered compose file.
   `--force-recreate` applies the new hook mount. The LinuxServer Transmission
   image already supplies `unrar`, `7z`, and `tar`; no custom image is needed.

   ```bash
   docker compose up -d --force-recreate transmission
   ```

4. Verify it with a completed release, then inspect the container log:

   ```bash
   docker logs transmission 2>&1 | grep extract-archives
   ```

The hook uses the `TR_TORRENT_DIR` and `TR_TORRENT_NAME` values supplied by
Transmission and writes the media alongside the archive. No Sonarr custom
script is required. For Sonarr import, keep the two containers on a common path:
configure Transmission's download directory as `/data/meta/downloads` (both
containers mount `/mnt/storage` at `/data`), or retain/add Sonarr's existing
remote-path mapping from `/downloads` to `/data/meta/downloads` if Transmission
uses its `/downloads` mount.

For a manual test inside the container, supply the directory arguments as
Transmission would:

```bash
docker exec \
  -e TR_TORRENT_DIR=/downloads \
  -e TR_TORRENT_NAME='Release directory' \
  transmission /usr/local/bin/extract-sonarr-archives
```

If Sonarr initially records an import warning while a very large archive is
still being extracted, use **Wanted → Manual Import** after the hook completes;
the extracted video will be in the same release directory.
