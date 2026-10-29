# si storage recovery and disk replacement

Last updated: **2026-10-20 (HKT)**. All three 16 TB drive installations are
complete. Disk5 checksum validation, parity sync, and the final full scrub
passed; the final scrub finished at **11:45 HKT October 20**. The storage pool is corrected and application services were restored at
**12:27 HKT October 20**; some container health checks were still warming up. The 132 known incomplete
recovery files remain preserved, and old removed drives should remain intact.

## Current status and constraints

- The failed 8 TB data disk (`d4`) is dead and absent. Do not attempt to revive,
  image, test, or repair it. The later recovery step uses surviving disks and
  SnapRAID parity to reconstruct files onto a replacement disk.
- Application writers and scheduled maintenance are stopped, with persistent
  startup restrictions. The server was left powered on. Filesystems remain
  mounted; this is service containment, not a read-only storage snapshot.
- Both existing parity disks remain intact. **Do not sync or scrub before
  recovery has been assessed and accepted.**
- Readable content files are dated December 24, 2025. All four copies match,
  but that does not prove parity freshness, consistency, or recoverability.
- `/meta/` is excluded from SnapRAID. Application data and synced configuration
  there require independent backups; parity cannot reconstruct excluded files.
- New files on surviving disks remain available. Unsynced files on the failed
  disk are not protected by the old parity. Changes/deletions on surviving disks
  can also prevent recovery of some older files on the failed disk.
- Recheck mounts and serials before every hardware operation. Device letters
  changed after reboot: `/dev/sde` is now parity-2, not the failed disk.
- Keep writers stopped throughout the migration. Stage copies outside
  `/mnt/data/disk*`, which mergerfs automatically includes in `/mnt/storage`.

## October 13 drive assessment and confirmed purchases

Confirmed purchase: **three 16 TB drives total**. Allocate E to failed `d4`, C
to parity-1, and F directly to replace the old 3 TB `d5`. Retire A rather than
repurposing it. Keep existing data disk32; there is no fourth new drive for it.
Final nominal data capacity will be **64 TB** (8 + 16 + 8 + 16 + 16), with two
separate 16 TB parity drives.

After the user's physical replacement and reboot, live inspection at 23:25 HKT
identified E as **ST16000NM001G-2KK103 / ZL2GQ2JQ**, 16,000,900,661,248 bytes,
currently `/dev/sde`. Stable path:
`/dev/disk/by-id/ata-ST16000NM001G-2KK103_ZL2GQ2JQ`.
Initial inspection found GPT/Windows LDM partitions and an NTFS volume containing
only `System Volume Information/WPSettings.dat` (12 bytes). After explicit user
authorization, the Windows signatures/partition table were removed and E was
formatted directly as ext4, matching the whole-device layout of the other data
drives (`mkfs.ext4 -m 0 -T largefile -L disk42`).

Verified filesystem label: **disk42**; mount: **`/mnt/data/disk42`**;
UUID: **`9d49130f-b477-4990-b2c2-93ebebf2d0c6`**. `fstab` now mounts this UUID;
SnapRAID retains logical **`d4`**, with its data/content paths updated to disk42.
The filesystem is empty apart from `lost+found`. No recovery or sync ran.
SMART before formatting PASSED with 1,445 powered-on hours and zero reallocated,
pending, offline-uncorrectable, reported-uncorrectable and CRC counts.

The active mergerfs mount still has its original `/mnt/data/disk4` branch;
`disk42` has deliberately not been added to the application-facing pool yet.
The old directory was verified empty. Replace/remove that stale branch and
remove the empty old directory before restoring application access, otherwise
wildcard pooling could include an unmounted OS-filesystem directory.

Docker, Compose, Plex, cron and atd remain inactive; containerd is also inactive.
Both parity disks and all four surviving data disks are still mounted. The two
other newly purchased drives are not yet visible in the inventory.

| Existing role | Serial | Powered-on hours | Approx. powered-on years | RPM |
| --- | --- | ---: | ---: | ---: |
| B: data d5, 3 TB WD Green | WD-WMC4N0383817 | 90,194 | 10.3 | 5,400 |
| Data d3, 8 TB IronWolf | WSD33L2N | 45,581 | 5.2 | 7,200 |
| A: parity-1, 8 TB IronWolf | WSD3AQ81 | 45,580 | 5.2 | 7,200 |
| Data d1, 8 TB IronWolf Pro | WWZ16S74 | 19,866 | 2.3 | 7,200 |
| Data d2, 16 TB Toshiba | Y4U0A0G4FZ6G | 10,734 | 1.2 | 7,200 |
| D: parity-2, 16 TB Toshiba | 25L0A03PFQEH | 7,021 | 0.8 | 7,200 |

All six array HDDs report SMART PASSED with zero reallocated, pending,
offline-uncorrectable and UDMA CRC counts. B has 647,375 head load/unload cycles.
**B is the first retirement candidate** based on age, accumulated mechanical use,
capacity, and lower spindle speed. This does not establish an imminent failure
or measured performance ranking. Powered-on years are not calendar age.

The OS SSD separately reports 116,534 powered-on hours (about 13.3 powered-on
years). It is not a data-array replacement candidate; plan its backup/replacement
separately after stabilizing storage.

Evidence: [earlier SMART comparison](../troubleshooting/si-2026-10-13/smart-inventory.txt),
[post-replacement inventory](../troubleshooting/si-2026-10-13/post-replacement-inventory.txt),
and [replacement SMART/partition report](../troubleshooting/si-2026-10-13/replacement-disk-smart.txt).

## Disk roles

| Label | Current role | Final role | Model / serial |
| --- | --- | --- | --- |
| Failed disk | 8 TB data `d4` | Retired; retain offline | Not recovered |
| E | 16 TB, ext4 mounted as disk42 | Data `d4`, `/mnt/data/disk42`, label `disk42` | ST16000NM001G-2KK103 / **ZL2GQ2JQ** |
| A | 8 TB parity-1 | Retired; retain offline | ST8000VN004-2M2101 / **WSD3AQ81** |
| B | 3 TB data `d5` | Removed; retain as fallback | WDC WD30EZRX-00D8PB0 / **WD-WMC4N0383817** |
| F | New 16 TB purchase | Data `d5`, `/mnt/data/disk5` | Record when installed |
| C | 16 TB ext4, mounted as parity12 | Parity-1, `/mnt/parity/disk12` | TOSHIBA MG08ACA16TE / **Z4L0A0PHFWTG** |
| D | 16 TB parity-2 | Parity-2, `/mnt/parity/disk22` | TOSHIBA MG09ACA16TE / **25L0A03PFQEH** |

Other surviving data disks:

| SnapRAID name | Mount | Serial | Filesystem UUID |
| --- | --- | --- | --- |
| `d1` | `/mnt/data/disk12` | WWZ16S74 | `f28eba22-c264-4021-84b9-37e85420b3a3` |
| `d2` | `/mnt/data/disk22` | Y4U0A0G4FZ6G | `de5f6189-ffcf-4998-9eb6-f5c96455d35d` |
| `d3` | `/mnt/data/disk32` | WSD33L2N | `eb5d5636-dcc2-441b-a7b7-8c12297b4568` |

The failed disk's old UUID was `d32d6659-f024-44cf-afe3-8d4bdd1755b4`.
Full current identities, including both parity UUIDs, are in the
[saved inventory](../troubleshooting/si-2026-10-09/inventory.txt).

## Phase 1 — Freeze and preserve: complete

- [x] Stop all container tasks, Docker/Compose, Plex, cron, deferred jobs, and indexing.
- [x] Block automatic restart across reboot; record reversal instructions below.
- [x] Confirm Insync and SnapRAID are not running; scheduled SnapRAID sync was already commented out.
- [x] Preserve configuration, cron/startup settings, logs, serials, UUIDs, and mount mappings.
- [x] Copy all four readable SnapRAID content files to this computer.
- [x] Verify each archived content file against its source SHA-256 checksum.
- [x] Read existing SMART reports without starting self-tests. All present drives report PASSED; all six array HDDs have zero reallocated, pending, offline-uncorrectable, and UDMA CRC counts.
- [x] Leave the failed disk alone and both parity disks intact.

Evidence is local to this checkout under `troubleshooting/si-2026-10-09/`:

- [Maintenance report](../troubleshooting/si-2026-10-09/READ-ME.txt)
- [Content archive](../troubleshooting/si-2026-10-09/snapraid-content.tar.gz):
  8,233,139,451 bytes; four files of 2,086,399,445 bytes each.
- [Verification results](../troubleshooting/si-2026-10-09/content-verification.txt)
  and [source checksums](../troubleshooting/si-2026-10-09/content-source.sha256)
- [Configuration archive](../troubleshooting/si-2026-10-09/config.tar.gz)
- [SMART reports](../troubleshooting/si-2026-10-09/smart.txt),
  [service verification](../troubleshooting/si-2026-10-09/verification.txt), and
  [artifact checksums](../troubleshooting/si-2026-10-09/SHA256SUMS)

These artifacts are local, uncommitted evidence, not a backup of the pool's data
or parity files. Keep them available independently of `si`. SMART results are
not a surface test or a guarantee of reliability.

## Phase 2 — Replace failed disk and reconstruct d4: hardware installed; recovery pending

- [x] Obtain/install E (16 TB); record model, serial, and device capacity.
- [x] Recheck containment and all surviving mounts after installation; both parity disks retained.
- [x] User powered down and installed E in place of the failed disk.
- [x] Identify E by serial ZL2GQ2JQ; inspect existing partition layout and SMART.
- [x] Confirm existing Windows/NTFS contents are disposable.
- [x] Prepare E with filesystem label `disk42` and record its new UUID.
- [x] Replace the failed disk's `fstab` entry and mount E at `/mnt/data/disk42`; confirm the path is a real mount on E, not an empty directory on the OS filesystem.
- [x] Update to `data d4 /mnt/data/disk42` and `content /mnt/data/disk42/.snapraid.content`; preserve logical name `d4`.
- [x] Inspect old `/mnt/data/disk4`: empty directory, still referenced by the active mergerfs mount.
- [x] Confirm disk42 is in mergerfs; remove stale empty disk4 branch and directory before restoring applications (October 20).
- [x] Verify preserved content hashes and parity-file accessibility before initial fix; parity-2 consistency remains uncertain. Applications remain stopped.
- [x] Choose `/var/log/snapraid-recovery` on the OS disk (8.7 GB free at launch).
- [x] Complete initial reconstruction pass onto E (started 23:45:51 HKT October 13; finished October 14 with exit status 1 and unrecoverable errors):

  ```bash
  sudo snapraid -d d4 -l /var/log/snapraid-recovery/d4-fix.log fix
  sudo snapraid -d d4 -a check
  ```

- [x] Review initial fix summary and inventory 132 `.unrecoverable` files; final loss assessment still pending verification.
- [x] Complete detached `snapraid-d4-check.service`: 100% checked in 10:50, exit 1, 1,322,867 error events.
- [x] Analyze all 1,322,867 verification events: only open errors for exactly the 132 known `.unrecoverable` files; no additional checksum/read failures reported.
- [x] Confirm backup availability: user reports **no independent backups**; parity was the only intended protection and had not been synced for roughly nine months.
- [ ] Assess residual recovery options using surviving data and retained parity after verification; no external backup/import source is currently available.
- [x] User explicitly approved replacing the old parity baseline with the reviewed current dataset, accepting old snapshot paths no longer on the drives; retain all present files and partial files. Rebuild remains gated on preservation verification.

**Gate:** no sync yet. A sync replaces the old recovery baseline and can prevent
further recovery attempts. This phase does not access or attempt recovery from
the dead physical disk.

## Phase 3 — Install C and rebuild parity: prepared and mounted; rebuild pending

The existing 8 TB parity-1 cannot accommodate parity growing to the size of the
nearly full 16 TB data disk. Install C before establishing the new baseline.

- [x] User approved the reviewed current baseline on October 15; writers remain stopped. Preservation verification must finish before rebuild.
- [x] Server cleanly powered down; user replaced A. Retain A untouched offline.
- [x] Install/inventory C (16 TB), serial Z4L0A0PHFWTG; ext4 UUID `63c7eef8-6d74-4c0c-8404-c5830d141dcc`.
- [x] User explicitly authorized erasing existing EFI/APFS contents.
- [x] Prepare C as whole-device ext4, label `parity12`; mount at `/mnt/parity/disk12` by new UUID and update `fstab`.
- [x] Update SnapRAID parity paths:

  ```ini
  1-parity /mnt/parity/disk12/snapraid.parity
  2-parity /mnt/parity/disk22/snapraid.parity
  ```

- [x] Confirm all five data disks and both parity filesystems C/D are correctly mounted. New parity-1 file is absent until rebuild.
- [x] Run/review detached pre-rebuild diff (October 15): 508,349 added, 45,562 removed, 2 updated, 16,939 moved, 1,632 copied, 11,688 restored.
- [x] Obtain explicit user approval for replacing the old parity baseline, including old snapshot paths no longer on disk, and excluding `/docker/`; received October 15 after the initial automatic rejection.
- [ ] Establish and verify the accepted baseline:

  ```bash
  sudo snapraid --force-full sync
  sudo snapraid -p full scrub
  ```

- [ ] Record successful completion and resolve all errors before retiring A offline.

**Gate:** keep A's old parity intact until C/D verification succeeds. Updating D
also replaces its old recovery state, so A alone is not a complete rollback.

## Phase 4 — Copy B to new 16 TB F: pending

- [ ] Confirm C and D contain verified parity for the accepted dataset.
- [ ] Power down; temporarily disconnect D and connect F in its place.
- [ ] Record F's model/serial, inspect its existing contents, and confirm it is the intended disposable destination.
- [ ] Prepare F for data and mount it at `/mnt/staging/disk5`.
- [ ] Confirm source `/mnt/data/disk5` is B and staging destination is F. Leave A offline and unchanged.
- [ ] Copy all data and metadata directly from B:

  ```bash
  sudo rsync -aHAXS --numeric-ids --info=progress2 \
    /mnt/data/disk5/ /mnt/staging/disk5/
  ```

- [ ] Verify with a checksum-based dry run and investigate any differences:

  ```bash
  sudo rsync -aHAXScn --numeric-ids --delete --itemize-changes \
    /mnt/data/disk5/ /mnt/staging/disk5/
  ```

The `-n` makes this verification a dry run, including `--delete`.
Do not sync while D is disconnected; leave its parity configuration intact.
Do not expose the staging destination through mergerfs.

## Phase 5 — Final assembly and validation: pending

- [ ] After copy verification, power down; remove B and reconnect D.
- [ ] Keep B untouched as a fallback.
- [ ] Update `fstab` to mount F's new UUID at `/mnt/data/disk5`.
- [ ] Retain `data d5 /mnt/data/disk5` and corresponding content-file path.
- [ ] Confirm every mount by serial and UUID; ensure no staging duplicate is in the mergerfs pool.
- [ ] Run final validation, inspecting each result before the next command:

  ```bash
  sudo snapraid diff
  sudo snapraid -d d5 -a check
  sudo snapraid sync
  sudo snapraid -p full scrub
  ```

- [ ] Resolve unexpected differences or UUID protection errors; do not blindly override safeguards.
- [ ] Record the final disk map, config backup, sync/scrub results, and remaining losses.
- [ ] Establish an independent backup for `/meta/` and other irreplaceable data.
- [ ] Restore application services and maintenance only after validation.
- [ ] Configure and verify future SnapRAID scheduling separately; its old cron entry remains commented out.

## Maintenance startup restrictions and reversal

Applied on October 9:

| Scope | Change |
| --- | --- |
| System | Disabled `docker`, `docker.socket`, `dockers`, `plexmediaserver`, `crond`, `atd` |
| System | Masked `docker.service`, `docker.socket`, `plexmediaserver.service`, `crond.service`, `atd.service` |
| System | Masked `plocate-updatedb.timer`, `plocate-updatedb.service`, `fstrim.timer` |
| User `m` | Masked `localsearch-3.service`, `localsearch-control-3.service`, `localsearch-writeback-3.service` |
| User `m` | Disabled/stopped `backup-packages.timer` |

After Phase 5 is complete, remove only these maintenance restrictions:

```bash
sudo systemctl unmask docker.service docker.socket plexmediaserver.service \
  crond.service atd.service plocate-updatedb.timer plocate-updatedb.service fstrim.timer
sudo systemctl enable docker.service dockers.service plexmediaserver.service \
  crond.service atd.service
```

As user `m`:

```bash
systemctl --user unmask localsearch-3.service localsearch-control-3.service \
  localsearch-writeback-3.service
systemctl --user enable backup-packages.timer
```

These commands restore eligibility for startup; start services deliberately when
ready. Verify timer enablement after unmasking. `docker.socket` was originally
disabled, so do not enable it just to restore the prior state. Do not run an
unreviewed `dotjik apply` during maintenance: managed configuration may restore
startup settings. The reversal commands were executed on **October 20** after the final full scrub passed; see the restoration entry below.

## Activity log

| Date (HKT) | Work | Result / next step |
| --- | --- | --- |
| 2026-10-07 | Diagnosed failed `d4`; stopped writers and copied logs/configuration | Media errors, failed SATA resets, disk detached; no recovery or poweroff performed by agent |
| 2026-10-09 | Connected at `192.168.1.150` using Mullvad bypass and existing trusted SSH host key | Server had rebooted; applications had restarted |
| 2026-10-09 | Completed Phase 1 containment and metadata preservation | Persistent startup restrictions; all four content copies verified; both parity disks intact |
| 2026-10-13 | Read-only live inventory and SMART reassessment | B is the first retirement candidate |
| 2026-10-13 23:25 | User installed E; inventoried after reboot | Three new 16 TB drives confirmed; E serial ZL2GQ2JQ, requested disk42, existing NTFS remains untouched |
| 2026-10-13 23:34 | Formatted authorized E as ext4 disk42; mounted by UUID and updated d4 paths | Configuration backed up; parity untouched; recovery not started |
| 2026-10-13 23:45 | User launched detached d4 fix service; all four source hashes passed | Searching surviving disks; recovery completion pending |
| 2026-10-14 10:42–10:46 | Found OS disk full from 11 GB detailed log; preserved/verified log, reclaimed copied blocks, started log keeper and resumed recovery | Recovery around 48%; check both services and remaining space |
| 2026-10-14 ~17:40–17:55 | Initial fix pass completed; status verified at 17:55 | Exit 1; 28,701,620 recovered block errors, 423,455 unrecoverable block errors; 132 marked files inventoried |
| 2026-10-14 17:58 | Started detached read-only d4 verification | `snapraid-d4-check.service`; logs on disk42; no independent backups confirmed |
| 2026-10-15 | Analyzed entire verification log by file | All errors match 132 known marked files; no additional checksum/read failures |
| Pending | Assess/accept remaining losses after verification | Parity-2 consistency remains uncertain; pool branch switch still pending |

Reference: [official SnapRAID recovery procedure](https://www.snapraid.it/manual.html#sec4-4).

Preparation evidence: [format/mount log](../troubleshooting/si-2026-10-13/disk42-preparation.txt), [verification](../troubleshooting/si-2026-10-13/disk42-verification.txt), [before/after configuration archive](../troubleshooting/si-2026-10-13/disk42-config.tar.gz).

### Recovery launch observation: parity-2 identity mismatch

The fix process reported the expected d4 UUID change and an additional parity-2
UUID change from `eb5d5636-dcc2-441b-a7b7-8c12297b4568` (currently data disk32)
to `b052297a-044f-421d-ac6e-bafc60da8bf5` (current parity-2). This could reflect
an earlier parity-file migration; its consistency with saved metadata is not
confirmed. The current parity-2 file is 7,947,074,142,208 bytes with an August 29,
2025 mtime, while parity-1 is 7,999,309,217,792 bytes with a December 25, 2025 mtime.
Timestamps/sizes alone do not establish parity validity. Do not describe both
parity files as a verified matching set. The running `-d d4 fix` is still scanning;
no overrides or sync were run. Review checksum-verified recovery results and
unrecoverable blocks before accepting the recovered dataset.

### October 14 progress and full OS-disk intervention

At 10:42 HKT, recovery was active and reporting about 48% progress, with roughly
4.0 TiB allocated on disk42. Its detailed log had grown to 11,419,394,048 bytes
and filled the OS filesystem. The process (PID 5060) was briefly paused with
SIGSTOP. The complete available log was compressed and SHA-256 verified at:

`/mnt/data/disk42/meta/recovery-logs/d4-fix-before-root-full.log.gz`

A manifest records the original length/hash. The console log was also preserved.
Copied blocks in the original detailed log were hole-punched without changing
its inode, logical size, or the running process's write offset. This restored
about 8.8 GB available on the OS disk. Output already lost during the disk-full
interval cannot be recreated.

A detached `snapraid-d4-log-keeper.service` now copies subsequent detailed-log
bytes to `/mnt/data/disk42/meta/recovery-logs/d4-fix-continuation.log`, fsyncs the
copy, then reclaims copied whole blocks from the original sparse log. It stops
when recovery exits and pauses recovery if log preservation fails. Recovery was
resumed with SIGCONT. This directory is under SnapRAID's excluded `/meta/`.
The original detailed log is sparse and no longer contains its full earlier
contents; retain both the compressed prefix and continuation when reviewing.
The compact console log remains at `/var/log/snapraid-recovery/d4-console.log`.

Check both services and OS free space during recovery. This intervention did
not run sync, change parity, or establish successful recovery completion.

### Initial recovery result, verified October 14 at 17:55 HKT

The recovery service completed with exit code 1. SnapRAID reported 100% processed,
9,559,301 MB accessed in 17:51, 89,650,482 error events, 28,701,620 recovered errors,
and 423,455 unrecoverable errors. These counters describe block/error events,
not counts of lost files; the 100% figure means the pass finished, not that every
file was recovered.

A read-only filename inventory found **132 `.unrecoverable` files**, with no scan
errors. Their current logical sizes total **322,511,489,648 bytes** (about 322.5 GB,
300.4 GiB). These are partially or wholly affected files; their combined size is
not the amount of unrecovered data. The list does not measure unsynced files that
were absent from the saved metadata. Approximately 6.9 TiB is allocated on disk42;
file-by-file verification has not yet run.

The log keeper completed successfully and preserved continuation through source
byte 26,159,118,610. The OS filesystem still has about 8.8 GB free. Leave services
stopped and do not sync until verification and possible further recovery/import
have been assessed and the remaining losses accepted.

Evidence: [completion snapshot](../troubleshooting/si-2026-10-13/recovery-completion.txt),
[affected paths](../troubleshooting/si-2026-10-13/unrecoverable-files.txt),
and [affected file sizes](../troubleshooting/si-2026-10-13/unrecoverable-files.json).

### Detached verification started October 14 at 17:58 HKT

Unit: `snapraid-d4-check.service`. It rechecks the selected content-file SHA-256
before executing:

```bash
snapraid -d d4 -a -l /mnt/data/disk42/meta/recovery-logs/d4-check.log check
```

The `-a` option checks data against the saved file checksums without checking
parity. Both console and detailed logs are on disk42, under excluded `/meta/`.
This is read-only for recovered data and parity; it does not sync or repair.
The user confirmed there are no independent backups. There is no external
backup source for the earlier suggested import retry. Preserve partial files,
metadata and both parity disks until verification and residual options have
been assessed. No loss acceptance or sync has occurred.

Monitor with:

```fish
sudo systemctl status snapraid-d4-check --no-pager
sudo tail -c 4000 /mnt/data/disk42/meta/recovery-logs/d4-check-console.log | tr '\r' '\n' | tail -n 15
```

### Verification completion, checked October 15 at 09:09 HKT

`snapraid-d4-check.service` finished with exit status 1. Summary:

```text
100% completed, 7287096 MB accessed in 10:50
WARNING! There are errors!
1322867 errors
```

This is an error-event count, not a file count. Subsequent file-level analysis confirmed that all verification errors correspond
to the 132 previously marked files; no additional checksum/read failures were
reported. No SnapRAID process remains running. OS free space is 8.8 GB; disk42 has
about 6.9 TiB allocated and 7.7 TiB free. No sync or parity rebuild was started.

### Verification file analysis completed October 15

All **1,322,867** verification error events are `Open error` events for **132**
original paths. Those original paths are absent because each corresponding file
was renamed with `.unrecoverable` during fix. After decoding SnapRAID's `\d`
escape for a colon in one audiobook path, the affected set exactly matches the
132-file inventory captured after recovery. There are **zero additional failing
paths**, and no read/checksum mismatch events were reported for other files.
The contents inside the marked partial files have not been separately verified.
This result does not account for excluded or unsynced files missing from metadata.

See the [readable verification report](../troubleshooting/si-2026-10-13/d4-verification-report.txt)
and [structured analysis](../troubleshooting/si-2026-10-13/d4-verification-analysis.json).
Keep the marked files and original parity until residual recovery/replacement
choices and remaining losses are accepted. No files were renamed or deleted,
and no sync or parity rebuild was performed during this analysis.

### Physical identification of old parity-1

At the user's request, drive **WSD3AQ81** (ST8000VN004-2M2101, 8 TB; currently
`/dev/sdc`) was verified idle, unmounted from `/mnt/parity/disk1`, and put in
standby with `hdparm -y`. `hdparm -C` confirmed **standby**. Its parity data was
not modified. This is spindle standby, not electrical isolation. Monitoring or
other access may wake it; check the printed serial before removal and fully
power off the server before disconnecting cables. The old UUID remains in
`fstab`; no permanent drive reassignment or new parity rebuild has occurred.

### New parity-1 hardware inventoried October 15 at 09:50 HKT

After the user replaced old parity-1, C is **TOSHIBA MG08ACA16TE**, serial
**Z4L0A0PHFWTG**, capacity 16,000,900,661,248 bytes, stable device path
`/dev/disk/by-id/ata-TOSHIBA_MG08ACA16TE_Z4L0A0PHFWTG` (currently `/dev/sdc`).
It contains existing EFI and APFS partitions, both unmounted. APFS content has
not been inspected; standard APFS inspection utilities were not found on si.
Confirm the existing contents can be erased before preparing ext4 parity storage.
SMART PASSED with 3,472 powered-on hours and zero reallocated, pending,
offline-uncorrectable and CRC counts; no ATA errors logged. No self-test ran.

All five data disks, including disk42, and existing parity-2 remain mounted;
old A (WSD3AQ81) is absent. Storage applications remain inactive and no SnapRAID
job is running. No formatting, parity configuration update, or sync was performed.
Evidence: [new parity inventory and SMART report](../troubleshooting/si-2026-10-15/new-parity-inventory.txt).

### New parity-1 preparation completed October 15 at 09:56 HKT

Following explicit user authorization, serial **Z4L0A0PHFWTG** was revalidated
unmounted, then its EFI/APFS signatures and partition table were erased. It was
formatted as whole-device ext4 (`-m 0 -T largefile4`), label **parity12**, UUID
**`63c7eef8-6d74-4c0c-8404-c5830d141dcc`**. Mounting by UUID at
`/mnt/parity/disk12` was verified. The old active parity-1 fstab entry was replaced;
SnapRAID parity-1 now points to `/mnt/parity/disk12/snapraid.parity`.

All five data filesystems and existing parity-2 remain mounted. Applications
remain stopped and no SnapRAID process is running. The new filesystem contains
only `lost+found`; **no parity-1 file exists yet**. Existing parity-2 and old
removed parity-1 were not modified. No sync, rebuild, or scrub ran.
The next pre-rebuild step is reviewing `snapraid diff` and resolving/accepting
remaining losses before replacing the recovery baseline.

Evidence: [preparation log](../troubleshooting/si-2026-10-15/parity12-preparation.txt),
[verification](../troubleshooting/si-2026-10-15/parity12-verification.txt), and
[before/after configuration plus original partition table](../troubleshooting/si-2026-10-15/parity12-config.tar.gz).
The same pre-change files remain on si under
`/root/si-parity12-preparation-20261015/`.

### Pre-rebuild diff reviewed October 15

Read-only `snapraid-pre-rebuild-diff.service` completed with exit 2
(`summary:exit:diff`, differences found). The new parity file remains absent;
no sync or rebuild ran. All expected data and parity filesystems were mounted.

| Classification | Count |
| --- | ---: |
| Equal | 244,497 |
| Added | 508,349 |
| Removed | 45,562 |
| Updated | 2 |
| Moved | 16,939 |
| Copied | 1,632 |
| Restored | 11,688 |

452,091 additions are Docker internals under `/mnt/data/disk22/docker`. Excluding
`/docker/` from future parity is recommended for review, but has not been applied.
Docker volumes may contain persistent state; an exclusion is not an independent
backup and does not delete that directory.

45,426 removals are on surviving disks. In particular, 37,053 music-file removals
are on d1, and 5,260 book-file removals span surviving disks. These are changes
relative to the old metadata and may reflect reorganizations/deletions during
the sync gap; they must not automatically be classified as newly lost files.
There are 136 d4 removals: the 132 known marked files plus four Sherlock paths
also listed as additions and verified still present. The only two updated paths
are the Calibre metadata database and preferences backup on d5.

Before rebuilding, review the historical removals, remaining recovery losses,
and Docker inclusion choice. No UUID/deletion safety overrides were used.

Artifacts: [review report](../troubleshooting/si-2026-10-15/pre-rebuild-review.txt),
[all removed paths](../troubleshooting/si-2026-10-15/pre-rebuild-removed-paths.txt),
[structured analysis](../troubleshooting/si-2026-10-15/pre-rebuild-diff-analysis.json),
[summary snapshot](../troubleshooting/si-2026-10-15/pre-rebuild-diff-summary.txt).

### Docker persistence investigation completed October 15

User clarified that post-December-2025 additions are legitimate and must be
retained. A parity exclusion changes coverage, not retention; do not delete the
new media/library files or Docker storage during preparation.

Read-only audit of the actual Compose configuration found 22 services, only
explicit bind mounts, no declared named volumes, and one leftover anonymous
FlareSolverr volume whose `_data` directory is empty. No saved container records
remain after the earlier Compose shutdown, so deleted private writable layers
cannot be independently audited. Most persistent application state is outside
Docker's data-root, under `/mnt/storage/meta/appData/`. MariaDB specifically uses
`/appData/mariadb/config` on the OS disk (about 2.15 GB allocated).
All configured bind sources exist and inspected app-state directories are
nonempty; database integrity and completeness have not been established.
Audiobookshelf's `/mnt/storage/meta/appCache/audiobookshelf` contains metadata and
backups as well as caches and should not be assumed disposable.

**Recommendation:** excluding `/docker/` from parity is reasonable for the
current configuration, but preserve the persistent bind data separately.
`/meta/` is already excluded and OS-disk `/appData` is outside SnapRAID entirely.
Compose alone cannot recreate databases/settings/history/credentials/media.
No Docker exclusion has been applied and no Docker files were deleted.

The current Compose file, local Lidarr build context, Transmission hooks, Docker
daemon configuration and startup unit were archived locally and validated. The
archive may contain credentials and has restricted permissions. It does not
contain the multi-GB application state directories.

Artifacts: [readable audit report](../troubleshooting/si-2026-10-15/docker-persistence-report.txt),
[Compose/mount/volume inventory](../troubleshooting/si-2026-10-15/docker-persistence-audit.json),
[application-state inventory](../troubleshooting/si-2026-10-15/docker-bind-state-audit.json),
and [recreation configuration archive](../troubleshooting/si-2026-10-15/docker-recreation-config.tar.gz).
Services remain stopped. No sync/rebuild was run during this audit.

### Metadata backup audit completed October 15

No configured whole-`/meta/` mirror or backup was found in inspected server
schedules/scripts/upload state. Mergerfs spreads files across separate ext4
filesystems rather than mirroring them. `/meta/` remains excluded from SnapRAID.

Some app-local backups exist: five Sonarr/Radarr ZIPs under `/meta/backups` passed
ZIP CRC checks and contain their database plus configuration. Latest visible
Sonarr backup: **October 4, 2026** (on disk32). Latest Radarr: **September 28,
2026** (on disk22). Each archive has one physical copy in the inspected array;
they are same-server partial backups, not an off-server mirror of metadata.
No database integrity check or application restore was performed.

The R2 package-backup configuration/state covers selected home-directory assets,
not `/meta/appData`. No running/installed Insync client or matching user config
was found; the `/meta/insync` directory alone does not prove active sync. Remote
cloud contents or other computers were not audited, so independent copies outside
the inspected server configuration are not ruled out. Earlier user confirmation
of no independent backups remains the planning assumption.

See [backup audit report](../troubleshooting/si-2026-10-15/meta-backup-report.txt)
and [archive/physical-location evidence](../troubleshooting/si-2026-10-15/meta-backup-audit.json).
No backup job was started and no storage configuration was changed in this audit.

### Metadata preservation started October 15 at 11:11 HKT

User requested a copy of `/meta/` on a new drive, kept excluded from parity, then
continuation of the process. Destination is recovered data drive **disk42**, UUID
`9d49130f-b477-4990-b2c2-93ebebf2d0c6`, with about 7.7 TiB free at launch:

`/mnt/data/disk42/.recovery-preservation/2026-10-15/`

The destination is outside the live `/meta/` tree to avoid recursive copying and
is explicitly excluded via `exclude /.recovery-preservation/`. Existing
`exclude /meta/` remains. Configuration snapshots are saved under the destination's
`configuration/` directory before changing exclusions. No files are removed.

Detached unit **`si-meta-preserve.service`** performs only:

1. Verify all data/parity UUID mounts and stopped writers.
2. Size physical metadata directories conservatively and check destination room.
3. Copy the merged `/mnt/storage/meta/` to `meta/` using rsync with owners,
   permissions, timestamps, ACLs, xattrs, hardlinks and sparse-file handling.
4. Verify with a checksum/metadata dry run; retry copy if differences remain.
5. Copy and similarly verify `/appData/mariadb/config/` to `mariadb-config/`.
6. Record completion and stop. It does **not** sync, scrub or rebuild parity.

The standalone scan was slow in Plex metadata/thumbnails, so sizing is included
in the durable job. Current state at launch: **sizing_metadata**. Copy completion
and verification are pending, not yet claimed. The destination is private; it
may contain credentials and application databases. This is a same-server
preservation copy, not independent off-site protection.

State: `state.json` under the destination. Log directory: `logs/`. Successful
checks create `meta-verified.json` and `mariadb-verified.json`. Do not infer
completion from an active service; require state `complete` and both markers.

```fish
sudo systemctl status si-meta-preserve --no-pager
sudo cat /mnt/data/disk42/.recovery-preservation/2026-10-15/state.json
```

Automatic approval review **rejected** the proposed combined preservation and
parity-rebuild workflow because sync/scrub would replace the old recovery
baseline with unresolved historical removals and a Docker exclusion lacking
explicit approval. The rejected workflow was not run. The safer preservation-only
unit has no parity-writing stage and was approved/launched. Docker's exclusion
has **not** been applied. After verified preservation and final diff review,
obtain explicit approval for the baseline replacement and `/docker/` exclusion
before a rebuild. No attempt to bypass the rejection was made.

Artifacts: [preservation script](../troubleshooting/si-2026-10-15/meta-preserve-only.py)
and [startup verification](../troubleshooting/si-2026-10-15/meta-preservation-start.txt).

### Explicit approval and gated rebuild queued October 15 at 13:10 HKT

User approved excluding `/docker/` and rebuilding the reviewed current dataset,
clarifying that “historical removals” means files no longer on the drives but
still referenced by the old parity snapshot. This accepts that baseline update;
**no existing media, partial file, Docker directory or metadata is to be deleted**.
This new explicit approval resolves the prior automatic-review authorization gap.

Preservation is still running. At 13:10 HKT the copy had transferred approximately
**689 GB**; rsync's incremental file-list percentage is not a reliable percentage
of the final complete tree. Physical-directory sizing found approximately
1.496 TB of metadata plus 2.15 GB of MariaDB data (a conservative sum that may
count duplicate paths). Checksum verification has not yet passed.

Detached **`si-parity-rebuild.service`** has been approved and started in phase
**`waiting_for_verified_preservation`**. It does not run SnapRAID while waiting.
It requires the preservation service to finish successfully and both
`meta-verified.json` and `mariadb-verified.json` to identify the correct source
and destination with verified=true. Failure or premature stop halts continuation.

After that gate it will:

1. Revalidate all mount UUIDs, stopped services and absence of another SnapRAID job.
2. Back up the configuration and add the approved `/docker/` exclusion while
   keeping `/meta/` and `/.recovery-preservation/` excluded.
3. Run a fresh diff. Require exactly the same removed-path set as the reviewed
   diff, no Docker/preservation scan entries, 56,258 additions and 2 updates.
   Any discrepancy halts before parity is changed.
4. Run `snapraid --force-full sync`, logging on disk42.
5. Only after successful sync, run a full scrub. Services remain stopped afterward.

No UUID, empty-disk or deletion-safety override is used. This is an approved
continuation of the new-baseline plan, not an attempt to bypass the earlier
rejection. **No rebuild was running at the 13:10 check.**

Rebuild state is separate from preservation state:

```fish
sudo systemctl status si-meta-preserve si-parity-rebuild --no-pager
sudo cat /mnt/data/disk42/.recovery-preservation/2026-10-15/state.json
sudo cat /mnt/data/disk42/.recovery-preservation/2026-10-15/rebuild-state.json
```

Artifacts: [approved continuation script](../troubleshooting/si-2026-10-15/authorized-parity-rebuild.py)
and [queued-state verification](../troubleshooting/si-2026-10-15/approved-rebuild-queued.txt).

### Continuation check October 15 at 13:24 HKT

User reaffirmed proceeding with the approved plan. Both detached units remain
active. Metadata copy has transferred approximately **801 GB**, with an average
reported rate around **98 MB/s**. Incremental rsync percentages can change as the
remaining tree is discovered. Preservation is still in `copying_meta`; checksum
verification and the MariaDB copy remain pending. The rebuild continuation is
correctly in `waiting_for_verified_preservation`, with no SnapRAID job running.
OS free space is 8.8 GB and disk42 has about 7.0 TiB free. No intervention or
restart was necessary; the existing detached sequence continues automatically.

### Preservation verified; UUID safeguard diagnosed October 15 at 22:04 HKT

Both preservation copies completed successfully at **20:53 HKT**. `/meta/`
checksum verification ran from 15:23 to 20:53 with no differences/errors; MariaDB
was then copied and checksum-verified. Both verification markers report success.
The final diff passed exactly: 56,258 added, 45,562 removed, 2 updated, same
removed-path SHA-256, zero Docker or preservation scan entries. The approved
`exclude /docker/` is now applied; no Docker files were deleted.

The initial sync attempt stopped before creating new parity-1 because SnapRAID
reported multiple UUID changes: replacement d4, replacement parity-1, and the
previously identified historical parity-2 relocation. Old parity-2 was unchanged.
Every present disk was rechecked by serial and mount UUID against the approved
inventory. All five data and both parity filesystem mappings match; services
remain stopped. This establishes that the UUID changes are intentional for the
approved baseline, rather than a missing/wrong mount.

A detached retry **`si-parity-rebuild-uuid-retry.service`** now repeats both
preservation-marker checks, all seven mount/serial checks and the exact final
diff gate, then runs `snapraid --force-full --force-uuid sync`. The UUID override
is scoped to this verified replacement rebuild; no empty-disk or zero-size
safety override is used. Full scrub follows only a successful sync. This updates
the earlier statement that no UUID override would be used: it became necessary
only after SnapRAID identified the known multiple replacement UUIDs.

Logs use `uuid-retry` names so the initial failed-at-safeguard evidence remains.
The common `rebuild-state.json` tracks the current retry. Do not report the old
`si-parity-rebuild.service` failure as the current retry's status.

Artifacts: [retry script](../troubleshooting/si-2026-10-15/authorized-parity-rebuild-uuid-retry.py)
and [retry startup state](../troubleshooting/si-2026-10-15/rebuild-uuid-retry-start.txt).

### Parity rebuild and full scrub completed October 18

Live status checked **October 18 at 14:45 HKT**:

- Full parity rebuild ran from October 15 at 22:06 to October 17 at 02:26
  (approximately **28 hours 20 minutes**) and reported `Everything OK`.
- The full scrub ran from October 17 at 02:26 to October 18 at 06:31
  (approximately **28 hours 5 minutes**) and reported `Everything OK`.
- `si-parity-rebuild-uuid-retry.service` finished with `Result=success` and
  `ExecMainStatus=0`; its state file records `phase=complete` at
  `2026-10-18T06:31:42.548616+08:00`. No SnapRAID process remains running.
- Root retains 8.8 GB free; disk42 retains 6.4 TiB free.
- Applications remain stopped. Next hardware phase is replacement of the old
  3 TB d5 with the third 16 TB drive, with copy and checksum verification before
  retiring the old disk. The known incomplete files remain incomplete; this
  successful scrub validates the accepted current baseline.

Remote evidence remains under
`/mnt/data/disk42/.recovery-preservation/2026-10-15/`, including
`rebuild-state.json`, `logs/parity-rebuild-uuid-retry-console.log`, and
`logs/parity-scrub-console.log`.

### Final data-drive replacement started October 18 at 15:17 HKT

The physical swap differed from the original staging plan: **parity-1 C**
(serial `Z4L0A0PHFWTG`, UUID `63c7eef8-6d74-4c0c-8404-c5830d141dcc`)
is disconnected; **parity-2 D** (`25L0A03PFQEH`) remains mounted. This is
acceptable for the copy stage. Do not run SnapRAID until parity-1 is reconnected.
For final assembly, remove old B and reconnect **C**, rather than D.

New F: Seagate `ST16000NM001G-2KK103`, serial **ZL2GRR5L**, 16 TB.
SMART passed: 1,446 powered-on hours; zero reallocated/pending/uncorrectable
sectors and CRC errors. The exFAT partition contained only Windows metadata
(`IndexerVolumeGuid`, `WPSettings.dat`, recycle-bin `desktop.ini`). It was
inspected read-only and unmounted. User explicitly approved formatting F and
starting the detached copy/checksum job.

`si-disk5-replacement-copy.service` started at 15:17. Its workflow verifies
source serial/UUID, destination identity/size, stopped applications, and absence
of SnapRAID before preparing F as whole-disk ext4 with label `disk5`. It mounts
F at `/mnt/staging/disk5`, outside the mergerfs branches, copies from old B
with `rsync -aHAXS --numeric-ids`, and then runs a checksum/metadata dry run
with `-aHAXScn --delete --itemize-changes`. `/lost+found/` is excluded from both
passes. No actual delete or parity sync is performed. Verification must produce
zero differences and diagnostics before recording completion.

Source remains `/mnt/data/disk5`, serial **WD-WMC4N0383817**, UUID
`a6adc4a9-6f78-487a-92f4-8f1eb339343f`, with about 2.5 TiB used.
Applications remain stopped; fstab and SnapRAID configuration remain unchanged.

Remote job state/logs and the original partition-table/configuration copies:
`/mnt/data/disk42/.recovery-preservation/2026-10-18-disk5/`.
Local reviewable workflow:
[copy script](../troubleshooting/si-2026-10-18/disk5-replacement-copy.py).
At the first check the job was active and formatting the filesystem; copying
and verification completion remain pending.

Formatting completed successfully with ext4 UUID
`0c11d7dc-cebf-4cb4-85c7-c6c132f843e7`. The first mount attempt failed because
the udev UUID link was not yet available. The link appeared subsequently; a
separate resume workflow rechecked the drive and mounted it without formatting
again. **Active unit: `si-disk5-replacement-resume.service`**. At **15:18 HKT**,
state is `copying` and `/mnt/staging/disk5` is mounted from the new drive.
[Resume workflow](../troubleshooting/si-2026-10-18/disk5-replacement-resume.py).
Both workflows use the same state/log directory above. After verification,
reconnect parity-1 C in place of old B; keep new F at the permanent disk5 path.

### Final hardware swap prepared October 18 at 23:26 HKT

Copy completed at **22:47 HKT**, transferring **2,724,422,252,026 bytes** in
**7h 28m 37s**. Checksum verification began immediately afterward. At 23:25,
it remained active with zero bytes in both differences and error logs; this
is not a completed verification result. User explicitly requested proceeding
without waiting for verification. The read-only verification service was
stopped; **checksum verification has not passed**.

After serial/UUID checks and confirming copy completion and stopped writers,
`/etc/fstab` was backed up as `fstab.before-final-swap` in the remote job directory
and updated to mount new F UUID `0c11d7dc-cebf-4cb4-85c7-c6c132f843e7` at
`/mnt/data/disk5` on the next boot. SnapRAID configuration was unchanged.
`final-swap-state.json` records the explicit incomplete-verification status.
A clean shutdown was requested for the physical swap.

Physical instructions: remove old 3 TB **WD-WMC4N0383817**, retain it intact;
leave new 16 TB **ZL2GRR5L** installed; reconnect parity-1 **Z4L0A0PHFWTG**.
After boot, verify all identities/mounts and the copied d5 data against saved
SnapRAID checksums before any parity sync or application restart. Direct
source/destination checksum verification remains incomplete and can be resumed
if the old drive is reconnected later.

### Final assembly inventoried October 18 at 23:35 HKT

All seven expected array mounts were verified by both UUID and serial. New F
`ZL2GRR5L` is mounted at `/mnt/data/disk5`, both parity C and D are mounted,
and old B is absent. Application services remain inactive; logical d5 and its
SnapRAID configuration are unchanged.

Detached `si-disk5-final-validation.service` started at **23:35 HKT**. It
rechecks all seven mount UUIDs/serials and stopped writers, then runs a SnapRAID
diff. Only a zero-exit diff permits the read-only `snapraid -d d5 -a check`.
Any changes/errors stop the workflow for review. It does not run parity sync.
State: `final-validation-state.json`; logs: `final-diff-console.log`,
`final-diff.log`, `final-d5-check-console.log`, `final-d5-check.log`, all under
the existing remote `2026-10-18-disk5` preservation directory.
[Validation script](../troubleshooting/si-2026-10-18/final-disk5-validation.py).
The initial status is `reviewing_diff`; completion is pending.

### Automatic final sync queued October 19

User explicitly requested automatic parity sync after the current validation
stage finishes. Detached **`si-disk5-final-sync.service`** is queued and waits
for `si-disk5-final-validation.service` to finish successfully and its state to
record `check_passed_awaiting_sync_review`. It then revalidates all seven mount
UUIDs/serials, stopped writers, absence of another SnapRAID process, and a
fresh zero-exit diff before running **normal `snapraid sync`**, without force
flags. Any failed gate or command stops the workflow; applications remain
stopped. This continuation does not run the final scrub.

Remote state: `final-sync-state.json`; logs: `final-sync-workflow-console.log`,
`final-pre-sync-diff-console.log`, `final-pre-sync-diff.log`,
`final-sync-console.log`, `final-sync.log`, in the existing disk5 preservation
directory. [Queued sync workflow](../troubleshooting/si-2026-10-18/final-parity-sync.py).

### Disk5 check and sync passed; final scrub started October 19

Checked live at **10:42 HKT**. `si-disk5-final-validation.service` passed with
exit 0 at **02:37 HKT**. Disk5 check accessed **2,714,759 MB in 3h 00m** and
reported `Everything OK`. The automatic continuation rechecked the file diff
and completed normal parity sync at **02:39 HKT**, exit 0. Both services are
inactive/successful; the new d5 identity has been accepted without force flags.

The final full scrub from Phase 5 was then launched as detached
**`si-disk5-final-scrub.service`** after rechecking seven mount UUIDs/serials,
stopped writers, absence of other SnapRAID processes, and sync success.
Applications remain stopped. Scrub completion and application restoration
remain pending. Previous full scrub took about 28h 5m; this is a rough planning
reference, not a live ETA for the current pass.

State/logs in the existing disk5 preservation directory:
`final-scrub-state.json`, `final-scrub-console.log`, `final-scrub.log`,
`final-scrub-workflow-console.log`.
[Final scrub workflow](../troubleshooting/si-2026-10-18/final-full-scrub.py).

### Final full scrub passed October 20 at 11:45 HKT

Live status verified at **12:17 HKT**. `si-disk5-final-scrub.service` is
inactive with `Result=success`, `ExecMainStatus=0`, and state `complete` at
`2026-10-20T11:45:00.734725+08:00`. The console ends with `Everything OK`.
Elapsed time from October 19 at 10:43 was approximately **25h 2m**. No SnapRAID
process remains running. Root has 8.8 GB free; disk42 has 6.4 TiB free.

Disk5 checksum verification, final parity sync, and final full scrub are now
complete. Remaining operational work: inspect/resolve stale mergerfs branches,
restore application services and intended maintenance, verify application health,
and record the final inventory. Backup/sync scheduling remains a separate task.
The full scrub validates the accepted current dataset; known incomplete files
remain preserved and are excluded from parity.

### Storage pool corrected and application restoration started October 20

Removed only the confirmed empty, unmounted `/mnt/data/disk4` directory and
its live mergerfs branch. Verified the pool now contains exactly disk12,
disk22, disk32, disk42 and disk5; no staging duplicate is present. The fstab
wildcard will expand to those same five directories on subsequent boots.
Pool capacity reports about 58 TiB total and 20 TiB available (64 TB nominal).
Branch snapshots are preserved in the remote disk5 evidence directory.

Removed the documented maintenance masks and restored enablement/startup of
Docker, Compose (`dockers`), Plex, crond and atd. fstrim and plocate timers are
enabled and started. Docker socket remains disabled for boot as originally
configured. User localsearch masks were removed and backup-packages.timer
was enabled/started. SnapRAID periodic scheduling remains a separate task.

At initial health checks Plex returned HTTP 200, Docker was active, and Compose
was starting containers, including dependencies waiting for health checks.
[Final verification diagram](assets/si-recovery/final-verification-passed.png).

Restoration verified at **12:27 HKT**: `dockers.service` completed successfully;
all **22 Compose containers are running**, MariaDB and Transmission report
healthy, and Plex returns HTTP 200. Some other configured container health
checks remain in startup grace periods. Navidrome restarted twice during startup
and subsequently logged that its server is ready; longer-term stability has not
yet been established. No user-level browsing/playback test was performed.
Application startup is restored. Independent backups and recurring SnapRAID
scheduling remain follow-up work; known incomplete files and preservation
snapshots remain retained.

### Public Sonarr access diagnosed October 20

`shows.type.hk` returned Cloudflare HTTP 523. Sonarr itself is running and
its direct LAN URL `http://192.168.1.150:8989/` returns HTTP 200 after redirect.
nginx has failed since boot: `ngx_http_dav_ext_module.so` reports module
version 1030004 while nginx expects 1030005. Public routing may also require
checking the origin address/port forwarding; the 523 alone does not isolate
that path. No proxy package/configuration changes were made in this diagnosis.
Sonarr also logged media-file permission errors, requiring separate review.
[HDD roles diagram](assets/si-recovery/hdd-layout.png).

### nginx module mismatch repaired October 20 at 13:03 HKT

nginx 1.30.5 was loading stream and custom WebDAV modules built for 1.30.4.
Updated only nginx-mod-stream and nginx-mod-devel to Fedora 1.30.5 packages.
Rebuilt WebDAV 3.0.0 from upstream tag v3.0.0, pinned commit
`f5e30888a256136d9c550bf1ada77d6ea78a48af`, using the installed Fedora nginx
module macros and 1.30.5 headers. Installed the resulting
`nginx-mod-dav-ext-3.0.0-4.fc43.nginx1.30.5.x86_64` RPM. Its package now declares
the nginx ABI requirement. Existing nginx/WebDAV site configuration was preserved.

`nginx -t` passed and nginx started successfully, listening on 443 and 8443.
Local HTTPS requests reach nginx and receive the expected rejection without the
configured Cloudflare client certificate. Sonarr itself previously passed its
direct LAN HTTP test. Public shows.type.hk access is not yet confirmed restored;
origin routing needs separate diagnosis. No TLS/client-certificate protections
were disabled.

Backup of configuration and old WebDAV module:
`/mnt/data/disk42/.recovery-preservation/2026-10-20-nginx/nginx-before-module-repair.tar.gz`.
Build sources, logs and RPMs:
`/home/m/.local/state/nginx-repair-2026-10-20/` on si.
[Rebuild spec](../troubleshooting/si-2026-10-20/nginx-mod-dav-ext.spec).
RPM queries also showed duplicate old/new nginx core package records; these were
not broadly cleaned up as part of this targeted module repair.

### Applications stopped again for network isolation October 20, about 13:08 HKT

User reported saturated internet and requested shutting services down for a
one-at-a-time investigation. All 51 Transmission torrents had already been
verified stopped. Stopped Compose via `dockers.service` (compose down), Plex,
nginx, crond, atd, Docker daemon/socket, and user backup-packages timer/service.
Verified no running Docker containers before stopping the daemon. SSH and
network connectivity remain available. This is a temporary stop; startup
enablement from restoration is unchanged. Do not start the aggregate dockers
service during investigation; bring individual Compose services up deliberately.

### Network isolation: services 1–3 restarted October 20

At user's request started Docker daemon alone, then MariaDB, then Sonarr using
`docker compose up -d --no-deps --pull never` per container. The aggregate
`dockers.service` remains inactive. Sonarr's usual Transmission dependency
was deliberately bypassed; Transmission and all other applications remain
stopped.

Measured physical Ethernet traffic over 15-second windows (RX/TX KiB/s):
Docker alone 0.06/0.01; MariaDB startup 0.52/0.21; Sonarr startup 1.63/1.12;
following Sonarr interval 0.03/0.01. MariaDB is healthy and Sonarr returns
HTTP 200. Only MariaDB and Sonarr containers are running. These short samples
show no saturation during startup, but do not rule out scheduled later activity.

### Sonarr historical-file audit October 20

Read-only audit found 1,009 episodes in current Wanted/Missing with no retained
prior file-path evidence in the checked history/backups. Sonarr automatically
unmonitors previously downloaded episodes whose files disappear, explaining why
outage candidates are absent from Wanted. Across all missing episodes, 467 have
historical file evidence (431 with paths); 232 across 51 series have
MissingFromDisk events during the outage/recovery period (48 October 9, 184
October 20). All 232 are now unmonitored in monitored series; 231 have historical
paths, 184 were linked to files in the October 15 database snapshot, and 96 match
known unrecoverable remnants. These are candidates rather than a proven count of
outage-caused losses. No monitoring, search, download or file state was changed.
[Report and CSV links](../troubleshooting/si-2026-10-20/sonarr-missing-episode-report.md).

### Sonarr monitoring restored and Radarr investigated October 20

At the user's request, enabled monitoring for all 232 reviewed Sonarr outage
candidates. Verified every episode is monitored and present in Wanted, now
1,241 episodes total. No searches or downloads triggered. The earlier audit's
"unmonitored" state above describes the state before this update.
[Change receipt](../troubleshooting/si-2026-10-20/sonarr-remonitor-receipt.json).

Started Radarr alone with `--no-deps --pull never`. Transmission remains stopped.
Radarr startup RX/TX measured 0.30/0.14 KiB/s over a short sample. Live API
shows an empty library (zero movies and Wanted); no library restoration performed.
Found valid September 21 and September 28 backups under `/meta/backups/radarr`,
separate from the application's own `Backups` directory. September 28 contains
4,611 movies, 3,112 linked files and 9,058 history records. SQLite quick_check
passed for both archives.

Of the 3,112 recorded files, 2,549 paths still exist; 551 absent old paths have
other video files in the same movie folder; 12 have no video in the recorded
folder. These 12 are candidates, not proven outage losses. Another five movies
have historical file events but were already unlinked in September and have no
current folder video. File-presence checks do not verify playback or integrity.
Next: preserve current Radarr state, restore historical library under download
containment, rescan files and reconcile newer additions before reviewing Wanted.
[Radarr report](../troubleshooting/si-2026-10-20/radarr-missing-movie-report.md)
and [candidate list](../troubleshooting/si-2026-10-20/radarr-missing-candidates.csv).

### Radarr backup restored October 20, 17:04 HKT

User approved restoring the September 28 backup and marking missing movies for
collection. Stopped Radarr and preserved the current database/config with matching
SHA-256 hashes under
`/mnt/data/disk42/.recovery-preservation/2026-10-20-radarr/20261020-170408/`.
Restored the backup database and configuration; integrity_check passed and the
live API confirmed all 4,611 library entries. Original backup ZIP remains intact.
[Restore receipt](../troubleshooting/si-2026-10-20/radarr-restore-receipt.json).

Disabled download clients, indexer activity and import lists during reconciliation;
original enable flags are recorded in the receipt. Transmission remains stopped.
An initial rescan revealed recovered root-owned files with mode 0600, unreadable
by Radarr (UID 1000, media GID 950). Stopped Radarr before relying on scan results.
An attempted named-user ACL grant was ineffective with this mergerfs mount;
rolled it back using saved ACLs. Granted media-group read access to exactly 737
unreadable regular files in `/public/movies`, preserving file ownership and
content; verified all were readable by Radarr's UID/group. Original group/mode
values are saved in `movie-group-permissions-before.json` in the preservation
folder. No blanket recursive permission change was used.

Restarted Radarr and launched a fresh filesystem-only `RescanMovie` at 17:07:42
HKT, command 2899744. Deferred the overdue metadata refresh while this scan runs.

The 17:07 scan stopped after 7m11s on `Legend of the White Dragon ()` with a
DirectoryNotFoundException during extra-file enumeration. Empty-folder cleanup
was enabled and the directory disappeared during the scan. Disabled
`deleteEmptyFolders` through Radarr's media-management API, saved the prior
configuration, and queued a fresh rescan (2899896). Two earlier subtitle-import
NullReferenceExceptions were also logged; these did not stop the movie scan.
The monitoring update is gated on successful rescan completion.


The corrected rescan completed successfully in 1m14s. Final library: 4,611
movies, 3,101 with recognized files, 1,510 without files. Verified all 1,510
missing movies are monitored (10 newly enabled), including all 12 identified
outage candidates. Wanted contains 1,398; the remaining 112 are monitored but
have unknown release years (`year=0`), which Radarr's Wanted query excludes.
SQLite quick_check passed. Automatic unmonitoring and empty-folder cleanup are
disabled. Download clients, indexers and import lists remain disabled until
network-isolation work permits deliberate reactivation. Transmission remains
stopped; no search/download was started.
[Restoration result and complete missing list](../troubleshooting/si-2026-10-20/radarr-restoration-result.md).

### Prowlarr restarted individually October 20

Started only Prowlarr using Compose `up -d --no-deps --pull never prowlarr`.
Verified HTTP 200 at `http://192.168.1.150:9696/` and opened the local login page
in the connected browser. API confirms eight configured indexers and five
application integrations. Ethernet RX/TX was 98.10/2.36 KiB/s during startup,
settling to 0.68/0.84 KiB/s in a second 15-second sample; no saturation observed.
Health reports unavailable indexer proxies, an unavailable 1337x indexer, and
unavailable Readarr/LazyLibrarian/Lidarr integrations. Supporting proxy and
application services have not been restarted; these warnings need reassessment
as services are restored. Running containers: MariaDB, Sonarr, Radarr, Prowlarr.
Transmission remains stopped; no aggregate stack start or searches initiated.

### ByParr restarted individually October 20, about 19:16 HKT

Prowlarr has two proxy entries: ByParr at `http://byparr:8191` and FlareSolverr
at `http://flaresolverr:8191`. Started only ByParr with `--no-deps --pull never`.
Opened `http://192.168.1.150:8191/docs` in the browser; HTTP 200 and Docker health
both passed. Verified `/health` from inside Prowlarr returns "Byparr is working!"
(version 3.0.4). Host Ethernet RX/TX during startup was 1,106.28/8.53 KiB/s,
settling to 0.08/0.04 KiB/s in the subsequent sample. ByParr's cumulative network
receive was 56.3 MB after startup; no sustained saturation observed.
FlareSolverr and Transmission remain stopped. Running containers: MariaDB,
Sonarr, Radarr, Prowlarr, ByParr. Next proxy to restore individually: FlareSolverr
(host port 8192).

### FlareSolverr restarted individually October 20, 19:19 HKT

Started only FlareSolverr with `--no-deps --pull never`. Opened its local status
page at `http://192.168.1.150:8192/`; HTTP 200 reports "FlareSolverr is ready!"
(version 3.5.2). Chromium startup self-test passed. Verified the same response
from inside Prowlarr using `http://flaresolverr:8191/`. Host Ethernet RX/TX was
2.75/1.67 KiB/s during startup and 0.08/0.01 KiB/s in the subsequent sample.
Transmission remains stopped. Running containers: MariaDB, Sonarr, Radarr,
Prowlarr, ByParr and FlareSolverr. No searches or downloads initiated.

### Lidarr restarted individually October 20, about 19:23 HKT

Started only Lidarr with `--no-deps --pull never`; opened the local login page
at `http://192.168.1.150:8686/` and verified HTTP 200. API reports 999 artists,
17,158 albums and 34,949 track files (database counts, not a fresh file-integrity
audit). Startup Ethernet RX/TX was 1.93/5.91 KiB/s, settling to 0.08/0.02 KiB/s.
Health reports the expected unavailable Transmission client and a stale 1337x
indexer warning. Tidal and Transmission download-client configurations are both
enabled; Tidal operates independently of Transmission. Verified Lidarr queue is
empty and no commands are active. No searches initiated or client settings changed.
Transmission remains stopped. Running containers additionally include Lidarr.

### Lidarr file audit and LazyLibrarian startup October 20, about 19:34–19:39 HKT

Read-only Lidarr audit checked all 38,604 raw TrackFiles records: every path exists,
none is empty, and all sizes match stored values. All 38,590 paths recorded in the
October 5 backup still exist; backup quick_check passed. Raw records include
unlinked files and differ from UI statistics. Wanted contains 446 albums. The
selected-release backlog within monitored artists/albums is 3,964 unlinked tracks
out of 5,032; this is exactly unchanged from October 5. Only 147/999 artists are
monitored. Found 14 mode-0600 Cardigans files unreadable by Lidarr's verified
UID 1000/GID 950, all without a current album association. No monitoring or file
permissions were changed. Path/size checks are not audio-integrity verification.
[Detailed report](../troubleshooting/si-2026-10-20/lidarr-missing-track-report.md).

Started LazyLibrarian alone with `--no-deps --pull never`. Startup installed its
configured `linuxserver/mods:universal-calibre` add-on and dependencies; logs
reported 131 MB of Ubuntu package downloads. Startup Ethernet RX/TX was
1,902.38/12.30 KiB/s, settling to 1.79/1.04 KiB/s. Verified HTTP 200 and opened
`http://192.168.1.150:5299/authors` in the browser. Transmission remains stopped.


### Lidarr permissions repaired and incomplete albums monitored October 20, 19:45 HKT

At the user's request, fixed the 14 identified Cardigans files by assigning the
media group (GID 950) and granting group read. Verified access as UID 1000/GID 950;
file ownership/content and locations were preserved. Original group/mode values
are saved under `/mnt/data/disk42/.recovery-preservation/2026-10-20-lidarr/20261020-194458/`.
These files remain outside the configured Cardigans artist folder and are not
implicitly imported or moved by a permission fix.

Within the 147 already-monitored artists, identified 621 incomplete albums across
selected releases (6,501 unlinked track entries). Enabled monitoring for the 175
previously unmonitored albums; all 621 targets are now monitored. Wanted increased
from 446 to 620 albums. The remaining target, Andy Stott's `Late Loop`, is monitored
but has a release date of October 30, 2026, so it is not yet in Wanted.

Disabled both Lidarr download clients (Tidal and Transmission) before changing
monitoring to preserve the download pause. Original enable flags were saved.
Verified both disabled and the download queue empty. No album searches initiated;
this restores Wanted/monitoring eligibility without starting downloads. No other
artists were enabled.
[Repair and Wanted receipt](../troubleshooting/si-2026-10-20/lidarr-repair-and-wanted-receipt.json).

### LazyLibrarian historical usage checked October 20

Compared live database with the October 6 database preserved October 15. Both
have the same 3 active authors, 1 wanted author, 3 recorded book files, 6 wanted
books and 13 failed historical download attempts. Paused-author counts differ
(150 preserved, 137 current), and catalog records increased from 483 to 489.
No evidence of a substantially larger active setup before the outage was found.
All three recorded ebook paths are stale, but matching filenames exist under the
current `/public/library/authors/` layout. Broader library contains 2,883 ebook
files across epub/mobi/azw3/pdf formats. Read-only investigation; no modifications.
[Usage report](../troubleshooting/si-2026-10-20/lazylibrarian-usage-report.md).

### Bookshelf restarted individually October 20

Started only Bookshelf (`ghcr.io/pennydreadful/bookshelf:hardcover`) with
`--no-deps --pull never`; Transmission dependency deliberately bypassed. Verified
HTTP 200 and opened `http://192.168.1.150:8787/` in the browser (login page is
branded Readarr). API reports 421 authors and 5,037 books; these are database
counts, not a file-integrity audit. Download queue is empty. Enabled client
configurations are Ephemera and Transmission, but neither container is running.
Health reports unavailable Transmission and a stale 1337x indexer warning.
Ethernet RX/TX was 10.45/1.62 KiB/s during startup and 10.19/1.82 KiB/s in the
subsequent sample. No searches, downloads or monitoring changes initiated.

### Bookshelf file audit; Audiobookshelf and Grimmory started October 20, about 20:14 HKT

Verified all 1,688 current Bookshelf BookFiles records exist, match stored sizes,
and are readable by UID 1000/GID 950. October 5 backup and October 9 preserved
database each contain 1,688 file records; all historical paths also exist and
match stored sizes. All three databases passed quick_check. No previously
recorded book-file loss found. Wanted lists 2,137 entries, which is not a count
of previously owned files lost. No library or permission changes made.
[Audit report](../troubleshooting/si-2026-10-20/bookshelf-missing-file-report.md).

Started Audiobookshelf and then Grimmory individually with `--no-deps --pull never`.
Opened and verified both local login pages:
`http://192.168.1.150:13378/audiobookshelf/login` and
`http://192.168.1.150:6060/login`. Both return HTTP 200; Grimmory's Docker health
is healthy and logs confirm seven existing libraries registered for monitoring.
Audiobookshelf startup host Ethernet RX/TX was 3.63/190.50 KiB/s, and an initial
post-start sample was 4.19/179.14 KiB/s. A subsequent idle sample settled to
0.66/0.31 KiB/s; new-container traffic was effectively flat over that interval.
Transmission and Ephemera remain stopped. No searches or downloads initiated.

### Grimmory missing-book records investigated October 20

Read-only DB/filesystem audit: all 2,911 file records for 2,910 active books exist
and are readable by app UID 1000/GID 950. Found 105 `deleted=1` records without
file rows or deletion timestamps. Cross-matching to active records found 64 same
ISBN matches, 18 normalized-title candidates, and 20 likely renamed counterparts.
Three old records remain unresolved: Sandman #14 (2833), Sandman #37 (2875), and
untitled record 2101. One candidate Stargate #5 filename has a #3 metadata title;
content identity is not verified. Collected Sandman PDFs exist but issue coverage
was not inspected. These are not 105 confirmed lost files. No cleanup/rescan or
mutations performed; latest retained library sync task is October 6.
[Full report and 105-book list](../troubleshooting/si-2026-10-20/grimmory-missing-books-report.md).

### Grimmory physical placement verified October 20

Mapped every active Grimmory file from the mergerfs pool to physical data mounts.
All 2,911 files for 2,910 active books (15,769,683,296 bytes) have exactly one
physical copy, all on data d2 at `/mnt/data/disk22/public/library/`. None is on
d1, d3, replacement d4 (`disk42`), or d5. The failed disk was d4; d2 remained in
the array. This placement explains why current indexed book files survived the
d4 failure. No `public/library/` entries occur in the saved 132-file
unrecoverable list. This is not a claim of content/checksum verification.
Grimmory's MariaDB data is separately stored at `/appData/mariadb/config` on the
OS root filesystem (`/dev/mapper/fedora_si-root`); application metadata lives at
`/mnt/storage/meta/appData/grimmory`. Container `/library` maps to the pooled
`/mnt/storage/public/library` path, while `/books` maps to its `stars` subfolder.
[Per-file physical mapping](../troubleshooting/si-2026-10-20/grimmory-disk-layout.json).

### Audiobookshelf audited October 20

Checked 1,360 items / 1,374 audio files against current disk and the preserved
October 9 DB. Two missing recordings exactly match known unrecoverable remnants:
Asimov's Mysteries (Lazar), and Books of Blood volumes 1–3 (Jim Zeiger). A Simon
Vance volumes 1–6 recording is present. 1,372 files survive; 483 are on replacement
d4 and the rest span the other four data disks. All local cover paths exist.

All catalog missing/invalid flags are false despite these losses; recorded last
full library scan is January 10. Two Three-Body Problem versions (Gary Tipton and
Bruno Roubicek) have exactly exchanged stored-vs-current sizes/durations, but both
headers parse and current narrator tags match folders; actual narration needs
content verification before any swaps. Black Sun's catalog title is correct,
while its folder/embedded tags are malformed. App-managed automatic backups are
disabled; preserved metadata copy exists. Read-only audit; no scans or repairs run.
[Collection report](../troubleshooting/si-2026-10-20/audiobookshelf-collection-report.md).

### Audiobookshelf repairs and next music services — October 20, 21:14–21:19 HKT

Preserved a consistent SQLite catalog snapshot and original Black Sun audio under
`/mnt/data/disk42/.recovery-preservation/2026-10-20-audiobookshelf/20261020-211449/`.
Created the app-managed `2026-10-20T2114.audiobookshelf` backup (75,134,602 bytes);
ZIP integrity test passed for all 2,941 entries. Enabled daily backups at 03:00 HKT,
retaining seven, under `/metadata/backups` (host
`/mnt/storage/meta/appCache/audiobookshelf/backups`). These are catalog/metadata
backups on the server, not copies of audiobook media on an independent device.

Corrected Black Sun embedded title/album, author and year to Black Sun,
Rebecca Roanhorse, 2020. Targeted item scans succeeded and reconciled both
Three-Body Problem size/duration discrepancies without swapping files or narrators.
The first targeted scan failed with SQLITE_BUSY and caused one app restart because
our audit script held a read cursor while calling the update API; retried successfully
with all cursors/connections closed before API calls. Full scan started 21:17:16;
completion verification pending at this log entry.

Started Navidrome (`:4533`) then Feishin (`:9180`) individually, without pulls or
dependencies. Opened both local login pages. Feishin was locked to public
`https://lp.type.hk`; changed its backend to LAN Navidrome and propagated the fix
into `native/home/files/dockers/docker-compose.yaml.j2`. Preserved original remote Compose at
`/mnt/data/disk42/.recovery-preservation/2026-10-20-audiobookshelf/feishin-compose-before.yaml`.
Navidrome began its initial library scan and logged some artwork/database-lock
warnings; it remains running. Transmission and Ephemera remain stopped.

Completed full Audiobookshelf scan at 21:25:15 HKT (7m58s): 2 added, 1,106
updated, 2 missing. Missing flags now exactly match the two known unrecoverable
recordings. Newly indexed existing recordings: The Dark Forest (P. J. Ochlan)
and Children of Ruin (Mel Hudson). Catalog now contains 1,362 items.

Corrected Black Sun's folder/file to
`/audiobooks/Rebecca Roanhorse/Black Sun (2020)/Rebecca Roanhorse - Black Sun (2020).m4b`.
Mergerfs changed the inode on directory rename, so the initial guarded rename was
rolled back. With the app stopped, saved `before-path-correction.sqlite`, changed
only the existing libraryItems record's path/relPath, then restarted and ran its
supported item scan. Initial history-schema checks failed before any mutation;
corrected them before proceeding. Same item and book IDs retained; all 101
listening-progress records verified unchanged. Database quick_check is OK and
all existing indexed audio files match stored sizes. Narrator identities were
not independently confirmed; no recordings were swapped.

Created final backup `2026-10-20T2127.audiobookshelf` (75,366,409 bytes), CRC test
passed for all 2,941 entries. Verified daily 03:00 HKT schedule and retention 7.
Full-scan logs also noted a pre-existing empty chapter title for Murder by Other
Means and rate-limited Google Books metadata lookups; no additional missing
recordings identified. Both music-service login pages verified in browser;
Feishin shows Navidrome as its configured backend.
[Repair verification](../troubleshooting/si-2026-10-20/audiobookshelf-repair-verification.json).

### Next two services: Tautulli and Plex Rewind — October 20

Started Tautulli and Plex Rewind individually with `--no-deps --pull never`.
Opened and verified local login pages at `http://192.168.1.150:8181/` and
`http://192.168.1.150:8383/`. Plex Rewind initially returned HTTP 500 because its
saved Tautulli URL `https://monitor.type.hk` returned Cloudflare 523. Preserved
settings in `/mnt/data/disk42/.recovery-preservation/2026-10-20-plex-rewind/settings-before.json`,
changed only `connection.tautulliUrl` in its persisted settings.json to
`http://tautulli:8181`, and restarted Plex Rewind. Browser now shows its normal
"Log in with Plex" page. This is an application setting stored in its existing
persistent volume, not an nginx/systjik setting. Plex itself was not started;
Transmission and Ephemera remain stopped. No media reacquisition initiated.

### Next two services: Shelfmark and Octo-Fiesta — October 20, 21:44 HKT

Started `shelfmark` and `octo-fiestarr` individually using `--no-deps --pull never`.
Shelfmark login opened at `http://192.168.1.150:8084/login`; persisted download_requests
and download_history tables both empty. Octo-Fiesta listens on port 5274 and proxies
Subsonic calls to `http://navidrome:4533`. Root URL returns 400 (missing endpoint);
opened `/rest/ping.view?v=1.16.1&c=service-check&f=json` instead, which returns HTTP 200
with Navidrome's expected missing-user authentication error. This verifies proxy
reachability, not authenticated playback. It has no standalone UI verified here.
No searches, playback or download requests issued. Transmission and Ephemera remain
stopped. Host RX/TX sample was 374.21/17.54 KiB/s; not attributed solely to these services.

### Next two services: Beets and Beets Audible — October 20

Started both independently without pulling images or requesting imports. Music
Beets eventually started but its web plugin bound to container loopback only.
Preserved config at `/mnt/data/disk42/.recovery-preservation/2026-10-20-beets/config-before.yaml`
and added `web.host: 0.0.0.0`, port 8337, readonly yes to its persistent config.
Restarted and opened the working Beets page at `http://192.168.1.150:8337/`.
Remaining plugin issues: custom copyartifacts imports missing beets.ui.get_path_formats;
custom stylize imports missing beets.ui.CODE_BY_COLOR. Neither was modified.
Beets Audible is running with an internal web listener but no published port.
Its init script exists but was skipped (non-executable); `beet version` lists
chroma, convert, embedart, fetchart, lastgenre, scrub, web, but not audible.
Needs plugin/config repair before audiobook importing. No imports, media searches,
or downloads requested; Transmission, Ephemera and auto-m4b remain stopped.

### Plex and local movie additions — October 20, 21:54 HKT

Started native plexmediaserver, verified active and opened LAN web UI at
`http://192.168.1.150:32400/web/`; browser redirects to a setup screen, no setup
changes made. auto-m4b remains stopped pending user response: its audiobook input
folders are populated and MAKE_BACKUP=N, so starting it could mutate existing media.
Transmission and Ephemera remain stopped.

Added all ten identified local 10_Sickest_Movies_of_all_time films to Radarr as
monitored 1080p, IDs 4663–4672, profile 4, no automatic search/grab. Interactive
searches found four with no matching seeded 1080p source; three more have sources
blocked by existing size/format rules, and three have acceptable seeded 1080p
candidates. Started detached rsync for the four local fallbacks at 2 MiB/s to
`/home/m/download/video/10_Sickest_Movies_of_all_time/`. Final SHA-256 verification
is automated; completion receipt pending. Local user unit is
`si-movie-fallback-copy.service`. Full external VIDEO copy not started: 336 GB
source exceeds 5.1 GB free on server /home.
[Movie report](../troubleshooting/si-2026-10-20/sickest-movies-report.md).

### Download-path correction and Plex database verification — October 20

Verified `/home/m/downloads` (plural) is a symlink to
`/mnt/storage/meta/downloads`; `/home/m/download` was a separate directory created
for the previous literal destination. The fallback copy completed and verified at
22:07:35 HKT. Moved its six files (1,592,569,867 bytes) to
`/home/m/downloads/video/10_Sickest_Movies_of_all_time`, checked every SHA-256 before
and after, and removed the empty mistaken directories. Updated the resume script
to the plural path. Full VIDEO copy still not initiated.

Plex uses `/var/lib/plexmediaserver` -> `/mnt/storage/meta/opt/plexmediaserver`.
Live library DB and October 15 preserved DB both contain Movies and Shows sections,
30,854 metadata records and 54,221 media_parts records. Dated DB/blob backups exist
for September 28, October 1, October 4. Live `/identity` reports claimed=0;
Preferences.xml has no PlexOnlineToken, username or FriendlyName. Preserved
Preferences.xml also lacks these. This indicates lost/unset account/setup state,
not an empty library DB. No restoration or setup changes made. Next step is
reclaiming the existing populated server with the user's Plex account; avoid
creating duplicate libraries. auto-m4b remains stopped; clarification concerns
its nonempty inputs and MAKE_BACKUP=N.

### Beets repairs completed; download clients audited — October 20

Music Beets custom plugins repaired for installed Beets 2.14.1: copyartifacts now
uses beets.util.pathformats.get_path_formats(config['paths']); stylize uses current
color constants with compatible ANSI rendering, legacy color names and NO_COLOR.
Temporary-file checks verified color rendering and sidecar copying while retaining
the source. Fixed fetchart initialization by mapping the existing Last.fm API key
to fetchart.lastfm_key and replacing the unsupported bandcamp artwork-source entry
with cover_art_url. The Bandcamp metadata plugin remains enabled. All configured
music plugins now load without errors; web endpoint responds HTTP 200.

Beets Audible now mounts the intended audiobook config, keeps its existing
/config/musiclibrary.blb catalog, and loads audible/copyartifacts/edit/fromfilename/
plex/scrub/web. Installed pinned compatible packages beets 2.14.1,
beets-audible 1.7.1, beets-copyartifacts3 0.1.7. Corrected init mount to
/custom-cont-init.d and supplied an executable, idempotent installation script.
Source changes are in native/home/files/dockers/docker-compose.yaml.j2 and
native/home/files/dockers/beets-audible-init/install-deps.sh. Existing audiobook config
is maintained in its server-side beets-audible checkout. Restart checked; no import
started. All items/albums/flexible-attribute rows compare equal to the saved catalog
(three items). Old configs/plugins/catalog preserved under
/mnt/data/disk42/.recovery-preservation/2026-10-20-beets-repair/.
Two non-fatal audiobook config deprecation warnings remain (musicbrainz.enabled,
audible.source_weight); plugin loading succeeds.

Transmission offline audit: 49 .torrent files, 67 .resume files. All 49 paired
resume files are paused. Thirteen unpaused resume files are orphaned, not paired
with a saved torrent; do not describe these as 13 active torrents. Global upload/
download limits are disabled, alt-speed is disabled, new torrents auto-start,
download concurrency is five and global peer limit is 200. Old destination paths
also exist among resume files; reconcile before resuming any jobs.
Ephemera has zero downloads and zero download requests, but downloads_paused=0.
Neither client was started or changed. Auto-m4b remains stopped per user request.
Next safe client-start preparation: preserve settings, ensure newly added jobs stay
paused, configure bandwidth limits, then start one client at a time and verify idle
traffic. No media acquisition or conversion initiated.

[Plugin patch](../troubleshooting/si-2026-10-20/beets-plugin-compatibility.patch) ·
[Verification](../troubleshooting/si-2026-10-20/beets-repair-verification.txt).

### Download clients started with downloads paused — October 21

Preserved Transmission settings and a consistent Ephemera database snapshot under
`/mnt/data/disk42/.recovery-preservation/2026-10-21-download-client-start/`.
Started clients individually. Transmission's live RPC confirms download limit
100 KB/s enabled (user requested connectivity testing only), upload limit 256 KB/s
enabled, and newly added torrents paused. All 51 loaded torrents are paused with
zero upload/download traffic at verification. Sonarr, Radarr, Lidarr and Bookshelf
Transmission connection tests passed; Radarr and Lidarr clients remain disabled.
No searches, grabs or torrent resumes were requested. Test receipt is
`connection-tests.json` in the preservation directory.

Ephemera is running at http://192.168.1.150:8286/ (HTTP 200), with
`downloads_paused=1`, zero downloads and zero download requests. Auto-m4b remains
on hold; no conversion started.

Video status: the selective six-file transfer (1,592,569,867 bytes) completed
October 20 at 22:07:35 HKT and was checksum verified, including after moving to
`/home/m/downloads/video/10_Sickest_Movies_of_all_time/`. The separate 336 GB
external VIDEO folder transfer has not started. The plural downloads path is
array-backed; the earlier /home capacity concern applied to the singular path.

### Four transferred movies imported through Radarr — October 21

ManualImport command 2900701 completed successfully at 00:35:56 HKT: Aftermath
(4663), August Underground's Mordum (4664), Cutting Moments (4668), and Guinea Pig
Part 2: Flower of Flesh and Blood (4671). Explicitly matched the two filenames
Radarr could not identify automatically. Used copy mode, preserving staged sources.
All four now have movieFile records and correctly renamed files in their existing
`/mnt/storage/public/movies/<Title (Year)>/` directories. SHA-256 hashes match the
staged sources for all four. Existing 1080p quality profiles remain unchanged;
these fallback files are SD (Radarr classified them as SDTV). No downloads started.
Radarr also imported the Guinea Pig subtitle; its original filename says Part 3
and 23.976 fps while the movie reports 25 fps, so subtitle identity/timing remains
unverified. The original NFO and all staged files remain available.
Receipt: `troubleshooting/si-2026-10-20/movie-manual-import-verification.txt`.

### Application-state backup priority and coverage audit — October 21

Live audit reconfirmed `/meta/`, `/docker/` and `/.recovery-preservation/` are
excluded from SnapRAID. Most container application state is in
`/mnt/storage/meta/appData`, physically on mergerfs data disks but outside parity
coverage. MariaDB instead mounts `/appData/mariadb/config` on the OS disk.
Audiobookshelf also requires `/mnt/storage/meta/appCache/audiobookshelf`;
Plex state is under `/mnt/storage/meta/opt/plexmediaserver`. Include deployment
files/hooks and server configuration in recovery coverage as well.

Read the October 15 preservation receipts live: state is complete and both meta
and MariaDB checksum/metadata verification succeeded at 20:53 HKT. This retained
copy is on disk42 in the same server. No whole-application-state backup job was
found in current system/user timers or inspected crontabs; the package-backup
user timer has no next run. App-local catalog backups do not establish independent
whole-server coverage.

Next: choose independent destination (user asked: local computer, USB disk or
existing cloud). Establish database-consistent backups, retained versions,
automatic scheduling, failure reporting and a restore test. Do not count live
SQLite/MariaDB file copies as verified consistent backups. No new backup schedule
or off-server transfer was enabled by this audit. Recursive size inventory is
still in progress; no current size estimate claimed.

### Private WGS storage and lean application backup sizing — October 21

Moved both sequencing `.fq.gz` files (87,934,561,570 bytes total, 81.90 GiB) from
`/mnt/storage/meta/appData/` into `/mnt/storage/private/wgs/`. Renamed each file
on its original physical disk, preserving device/inode/size and verifying the
merged destination. Owner is m; directory mode 0700 and files 0600. No file
contents copied or deleted. Private is not excluded by current SnapRAID rules;
new locations become parity-protected only after a successful future sync.
Move receipt: `troubleshooting/si-2026-10-21/wgs-move-receipt.jsonl`.

Read-only lean sizing excluded rebuildable caches, artwork, Docker/Flatpak files,
Plex thumbnails/metadata assets and package environments. Candidate measured
7.756 GiB including historical application backups. Existing historical backups
account for 740,380,595 bytes in appData, 3,443,127,654 bytes in Plex and
150,501,011 bytes in Audiobookshelf metadata. Current-state candidate is about
3.72 GiB uncompressed, including /etc, user settings/scripts, Compose and MariaDB;
server dotjik source and SSH files add only about 1.6 MiB. This is a sizing
estimate, not a completed consistent database snapshot. Some conservative
inclusions (user-installed binaries and logs stored inside database files) remain.
No existing backup archives or rebuildable assets were removed. Need a reviewed
per-application exclusion manifest before enabling the backup job; do not blindly
apply generic folder-name exclusions to potentially user-created artwork.
Sizing evidence: `troubleshooting/si-2026-10-21/essential-backup-size.jsonl`.

### Daily incremental application backups configured — October 21

Implemented [application backup practice](si-application-backups.md): Restic on
server and fi, encrypted repositories with separate keys, seven daily and four
weekly restore points, weekly pull of all retained points to fi at 2 MiB/s,
and a daily client freshness check. Server schedule is 04:00 HKT; weekly client
copy is Sunday 06:00 HKT; freshness check is 09:00 HKT. Small timer jitter applies.

Final workflow uses SQLite online backup plus quick_check (Plex tool fallback),
a locked native MariaDB logical dump, and staged configuration/scripts. No
scheduled application shutdowns. Both source repositories and configuration
keys are included. First accepted backup: 3.867 GiB logical / 1.942 GiB stored.
Small follow-up snapshot added 35.515 KiB, demonstrating deduplication.

Found Prowlarr index inconsistencies during validation. The backup copy passed
full integrity_check after rebuilding indexes; unrepaired evidence is included
in the encrypted backup. The live Prowlarr database remains unchanged.
An isolated MariaDB import and all-table check passed. All 21 production
containers and native Plex remained running after validation.

Source changes are persisted in dotjik and sibling systjik; unrelated checkout
changes were preserved. Server timer activated after the successful baseline.
Initial independent copy is running; client timer activation and restore checks
will be recorded after it completes.

Initial independent backup and verification completed October 21. Both retained
snapshots reached fi; all encrypted data packs passed read verification. A full
restore into a private temporary directory passed content verification. Radarr,
Sonarr and repaired Prowlarr passed full SQLite integrity checks; configuration,
Compose and configuration-decryption keys were present. Temporary restored files
were removed. SELinux labels were excluded for this cross-host rehearsal; the
runbook explains destination-policy relabeling on a real restore.

Weekly copy and daily health timers are active. Verified next runs:
server October 21 04:02:25 HKT; health October 21 09:03:41 HKT; weekly copy
October 25 06:03:08 HKT. Immediate freshness check passed. Final server retention
and repository check also passed. First network copy took roughly 17 minutes;
local verification is not bandwidth limited.

During the final service check, Transmission contained 62 torrents and some were
active. Paused the current queue per the earlier request; verified all 62 paused,
zero download traffic and the existing 100 KB/s limit enabled. No new searches
or downloads were requested by this backup workflow.

Receipts are in `troubleshooting/si-2026-10-21/`:
`server-backup-verification.json`, `local-backup-copy-receipt.json`, and
`local-backup-restore-verification.json`.


### October 21: daily offsite catch-up

Updated fi’s daily check to 10:00 HKT (up to five minutes jitter). It checks the latest Sunday 06:00 boundary and automatically copies/verifies retained snapshots if that weekly copy was missed. Current receipts must record a passed data check and correspond to a snapshot in the local repository. Catch-up has the same six-hour time allowance as the weekly transfer. All connections originate from fi; no sshd is needed there.

### October 21: missing-media CSV compilation

Compiled live read-only catalog exports and historical recovery evidence into
`/home/m/downloads/missing-media-2026-10-21/` on si, with local copies in
`troubleshooting/si-2026-10-21/missing-media/`. Includes 378 Navidrome missing
paths (all checked absent), 41 album groups, 1,516 fileless Radarr movies,
467 historically owned and still fileless Sonarr episodes, 1,251 current Wanted
episodes, 620 Lidarr Wanted albums, 2,137 Bookshelf Wanted books, two missing
audiobook recordings, two unresolved comic records and one unidentified book
record. Separate reconciliation and per-type recovery-evidence CSVs preserve
historical context. Counts overlap; Wanted is not evidence of outage loss.
README and manifest document provenance, uncertainty and CSV checksums.
No searches, grabs, downloads or monitoring changes were made.

### October 21: maintenance schedules and final application cleanup

Installed guarded daily 05:00 SnapRAID sync and Sunday 08:00 25%/seven-day scrub,
with up to ten minutes jitter and persistent timers. Both enabled and verified;
first sync is October 22. All seven UUIDs are pinned, no force flags used, diff
removals over 200 block the job. Current diff has 110 removals, passing the gate.
Known media writers pause only during sync, with finally/ExecStopPost/boot recovery.
Maintenance serializes with application backup. No immediate disk job was started
during the VIDEO transfer. Sources persisted in sibling systjik. See
[maintenance runbook](si-snapraid-maintenance.md).

Stopped only Prowlarr, preserved its database under
`/mnt/data/disk42/.recovery-preservation/2026-10-21-prowlarr-index-repair/`,
transactionally reindexed, verified full integrity and unchanged table counts,
and restarted it. The repair fixed History DownloadId and Date index errors.

Migrated Beets Audible source config from musicbrainz.enabled to
disabled_plugins and audible.source_weight to data_source_mismatch_penalty,
preserving values. Plugin loading is now free of both deprecation warnings.
Config-before is preserved under the dated beets-config preservation directory.

Created an owner-only recovery-key document on fi at
`~/.config/si-app-backup/RECOVERY-KEYS.txt`, outside version control. User should
store it independently in a password manager. No key values are recorded here.
Offsite connectivity remains deferred until the server is installed on site.
Media reacquisition and auto-m4b remain skipped as instructed.

Post-restart Prowlarr API responds and its live database again passes full
integrity_check. Beets Audible HTTP returns 200 and plugins load without the
old warnings. Subtitle inspection found 57 cues, ending at 2,516.315 seconds
inside the video's 2,518.8-second duration. Opening/closing text identifies the
Hideshi Hibino/April 1985 story consistent with Flower of Flesh and Blood.
No retiming or replacement was justified; exact dialogue synchronization still
requires listening. The misleading original subtitle filename is not evidence
that it belongs to a different film.

Automatic sync also refuses to proceed after a recorded scrub failure until a
successful scrub clears it. Recovery keys remain mode 0600 and were not printed.

### October 21: executable-release protection and television automation

Configured the [television-to-Plex flow](si-media-automation.md): Sonarr title
restrictions plus a 15-second torrent-manifest guard, safe non-executing archive
extraction using pinned Unpackerr 0.16.1, completed-download handling and episode
renaming, and tested Plex import notifications with container/host path mapping.
Disabled the previous extraction hook. Preserved existing bandwidth limits and
paused queues; no bulk reacquisition search was launched.

The single cached 992,648-byte Jujutsu Kaisen .exe was identified by its PE header,
quarantined with checksum verification and never executed. Current torrent
manifests contained no executable payloads at inspection. Guard tests passed;
Unpackerr retrieved the Sonarr queue and Plex's connection test passed. A real
new completed archive-to-library import was not available for end-to-end proof.
Managed changes persisted in dotjik/systjik; app secrets remain only in the
backed-up appData configs/databases. Pre-change state is in the dated media-flow
preservation directory.

### October 21: movie automation protection

Extended the existing payload guard to Radarr with per-application queue routing.
Added a -10,000 executable-title custom format to all seven movie quality profiles,
added Radarr to Unpackerr, and configured/tested Plex movie-import notifications.
Verified both guard routes preserve rejected download bytes. Live guard checks pass;
Radarr's download client remains disabled and no acquisition/backlog search started.
Pre-change state preserved in 2026-10-21-radarr-safety. See the media automation guide.
