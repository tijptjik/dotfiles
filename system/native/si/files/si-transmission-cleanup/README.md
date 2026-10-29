# Daily Transmission cleanup (Si only)

`si-transmission-cleanup.timer` runs daily at 04:30 Asia/Hong_Kong, with up to
15 minutes of jitter. `Persistent=true` catches a missed run after boot.
The service removes the torrent **and its download data** using Transmission RPC.

A torrent must have an exact Transmission label `sonarr`, `radarr`, `sonarred`,
or `radarred`, complete metadata, and all payload files downloaded. There is no
size threshold or permanent exception list. Unlabelled torrents and books with
only book labels are left alone. Labels alone do not prove an Arr import occurred;
this implements the requested label-based rule, without an Arr import-history check.

Public torrents qualify immediately. IPT torrents must have **more than 1,209,600
seconds (14 days)** of accumulated Transmission `secondsSeeding`. This is active
client seeding time, not time since completion and not the account's credited time.
Tracker downtime or accounting differences can make the two disagree; a reset or
re-added torrent can undercount. No IPT website login, cookie or passkey is needed.

IPT is identified by its observed tracker hosts `localhost.stackoverflow.tech`,
`routing.bgp.technology`, `ssl.empirehost.me`, and the exact `iptorrents.com` /
`iptorrents.me` domains and their subdomains. Matching IPT anywhere in a mixed
tracker list imposes the seeding requirement. Missing/malformed tracker metadata
and unknown private trackers are retained. Update the host list if IPT changes it.

The script defaults to dry-run, checks the hostname, takes an exclusive lock,
rechecks live eligibility before each removal, confines file verification to the
managed downloads, and refuses overlapping payloads used by other torrents.
Removal targets hashes rather than transient numeric IDs. A failed request or
verification fails the service; it does not retry an ambiguous removal request.
The Transmission RPC credentials come from the existing container environment and
are never written to source or logs. Only tracker hostnames are used for decisions;
announce URLs containing passkeys are not logged. Imported library hardlinks/copies
are unaffected by removing the download paths.

```sh
sudo /usr/local/lib/tjikup/tjikup system transmission-cleanup --dry-run
sudo systemctl start si-transmission-cleanup.service
systemctl list-timers si-transmission-cleanup.timer
journalctl -u si-transmission-cleanup.service
sudo cat /var/lib/si-transmission-cleanup/removals.jsonl
```

The private JSONL audit records intent before removal and verified success after
checking the torrent and its listed download files are gone. This is an audit log,
not a backup of deleted content. Disable future runs with
`sudo systemctl disable --now si-transmission-cleanup.timer`.

Tjikup ignores these files on every host except `si`; both units also use
`ConditionHost=si`, and the script independently refuses other hostnames.
