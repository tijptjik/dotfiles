# Extracting archived Sonarr releases

Sonarr does not extract release archives as part of import. Configure the
download client instead, so the extracted video is present before Sonarr's
completed-download handling scans the release. This repository installs
`~/.config/transmission/extract.fish` and mounts it into the LinuxServer
Transmission container as `/usr/local/bin/extract-sonarr-archives`.
It also installs a LinuxServer custom-init script that enables the completion
hook in the container's persistent `/config/settings.json` before
`transmission-daemon` starts.

The hook supports RAR (including `part01.rar` sets), ZIP, 7z (including
`.7z.001` sets), and tar archives. It extracts into the release directory,
recursively searches that directory, and never deletes the archive volumes;
that preserves Transmission seeding. Password-protected or incomplete archives
are logged as failures and left untouched.

## Enable the Transmission completion hook

1. Apply this repository so that the hook scripts and compose mounts exist:

   ```bash
   chezmoi apply
   ```

2. Start Transmission from the directory containing the rendered compose file.
   `--force-recreate` applies the hook and custom-init mounts. On every container
   start, the init script updates the live settings under `/config`; no manual
   edit of `/mnt/storage/meta/appData/transmission/settings.json` is required.
   The LinuxServer Transmission image already supplies `jq`, `unrar`, `7z`, and
   `tar`; no custom image is needed.

   ```bash
   docker compose up -d --force-recreate transmission
   ```

3. Verify startup configuration and then test it with a completed release:

   ```bash
   docker logs transmission 2>&1 | grep -E 'configure-archive-hook|extract-archives'
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
