# Codex floor-plan extraction on Si

The `codex-floorplans` manifest group installs a private extraction worker beside
Si's existing subscription-authenticated Codex VPN service. It does not replace
image rendering or enable a new public endpoint. No live deployment is performed
by adding this policy.

The reference implementation is HYPE's `scripts/floorplans/`; the four files in
`system/native/si/files/floorplans/` must be synchronized when changing the protocol.

Prerequisites: the existing Codex account login and VPN network, Python 3 with
Pillow, Poppler (`pdfinfo` and `pdftoppm`), and a root-owned 0600 environment file
`/etc/codex-vpn/floorplans.env` containing `FLOORPLAN_TOKEN`. Obtain and install the
credential using the established private BWS flow; never commit its value.

Apply only the `codex-floorplans` group through the existing native Tjikup manifest
and state directory, review the plan, then start `codex-floorplans.service`.
Do not blanket-apply the host manifest. The unit is not enabled automatically.

The worker listens on `/run/codex-floorplans/worker.sock` so it can retain the
Codex VPN namespace without exposing an unauthenticated listener. A separately
reviewed private reverse proxy must be able to access this socket and preserve
Authorization. Do not publish the socket through an unrestricted public route.
HYPE requires server-side `FLOORPLAN_WORKER_URL` and `FLOORPLAN_WORKER_TOKEN`
bindings. The browser never receives the credential or the worker URL.

Jobs accept at most 30 MiB and 12 PDF pages, queue eight jobs, and execute one at
a time. Source scans, logs and generated JSON remain in the 0700 state directory.
Set an operations retention policy before production use; source plans may be
private. HYPE copies completed page images and results into its private asset
bucket. Model output is an untrusted review draft and is validated before use.
No automatic publication, geographic placement, room identity creation or routing
is performed.

Verify with synthetic PDFs and mocked Codex output before sending building plans.
Then perform a subscription inference check, upload/poll round trip, source image
fetch and authenticated HYPE draft save. A running service alone does not prove
this integration works. See the activation record below for the deployed state.

The adapter now exposes `POST /jobs/:id/retry` for failed jobs using the retained
source. Restart recovery marks interrupted queued/running jobs failed, allowing an
explicit retry. HYPE retains the current building job pointer independently and
serves completed review data from its private bucket after worker shutdown.

The test-only fixture server and integration harness in HYPE are never part of
this manifest group. Production uses `extract.py` and the subscription Codex CLI.
Page ordering is numeric, including PDFs with 10-12 pages.

## Activation on 2026-11-24

The isolated service and authenticated proxy are active on Si at
`https://home.type.hk/hype-floorplans/`. Both the VPN and floor-plan service are
enabled for boot. Native receipts `receipt-MpzADL` and `receipt-m7i5KC` retain the
scoped installation. The managed-file check reports all seven files unchanged.
The proxy is an extension of the existing home.type.hk API snippet; its original
Atlas route was preserved. NGINX configuration validation passed before reload.

The dedicated BWS secret is `SI_CODEX_FLOORPLAN_TOKEN`, reference
`56821c2b-cab7-408c-9f32-b50c00a44846`. The Si home credential template supplies the
private environment file when the home group is applied. The current root
credential was installed directly from that BWS-backed secret; root runtime uses `/etc/codex-vpn/floorplans.env` (0600).
Do not print it. HYPE must use `User-Agent: HYPE-Floorplans/1.0`: the edge rejects
the generic Python urllib user agent before requests reach the worker.

Si's default Node is too old for the Codex CLI launcher. The scoped `codex.sh`
wrapper invokes `/usr/bin/node-22` without changing the system default. A real
original GBP page completed extraction after this fix and passed HYPE MapBundle
validation: two floors and 65 space polygons. This proves the endpoint and real
inference; production HYPE UI acceptance remains a separate check.

`X-Floorplan-Pages` selects up to 12 distinct original PDF page numbers. The
receipt retains `sourcePages` while rendered page filenames remain sequential.
Retries reuse that selection and the original source.

The real HYPE round trip also passed using local authenticated HYPE against this
production endpoint. Job `01655982-5aa1-49bb-b8d0-c941f73700ca` returned two
floors and 65 map polygons, then saved/reopened as an unpublished draft. Browser
evidence is HYPE runner `job-njhIGlaTvy`. Production account UI acceptance is
separate from this local-app/production-worker check.
