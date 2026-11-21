# Rahgard V2 — exact apex URL and conflict-safe cutover contract

**Owner decision:** The final V2 browser experience MUST run at **https://hinaa.ir/** (DNS apex, root `/`, standard HTTPS, trusted certificate). It must NOT be substituted by `https://rahgard.hinaa.ir/`, `www.hinaa.ir`, `http://hinaa.ir`, `hinaa.ir/v2` or an internal port URL. Keep the historical `rahgard.hinaa.ir` site, its data and all unrelated services unchanged unless separately and explicitly authorized.

**Authorization boundary:** Codex may audit, prepare scripts, test isolated images and restored databases, and submit a proposed immutable release. This document does not authorize live DNS/Arvan/TLS/Nginx edits, restarts, production database migrations, publication or external traffic cutover.

## Gate A — Read-only domain and VPS discovery

1. Confirm DNS/Arvan ownership and the current A/AAAA, CDN and origin routing of both `hinaa.ir` and `rahgard.hinaa.ir`, including redirect chains and exact public HTTPS responses. If the apex is already occupied by a different website or API, STOP and request a distinct owner decision about relocation/replacement. Do not assume an inaccessible domain is unused.
2. Read-only inspect the authorized VPS Nginx `server_name`, `listen`, SNI, port 63202 and 18080 listeners, certificates, NAT/firewall, Arvan HTTPS-to-origin trust and any other hosted services. Keep secret values and private keys out of evidence. Confirm a trusted SAN for **DNS:hinaa.ir**; `rahgard.hinaa.ir` alone is insufficient.
3. Record the read-only VPS application and database fingerprint, migration ledger and current PWA; integrate with the V2 real-data 0022/0023 rehearsal and backup gates. Do not overwrite existing live route or database to match a Git SHA.

Read-only examples (authorized operator only):

```bash
dig +short hinaa.ir A
dig +short hinaa.ir AAAA
curl -I --max-time 15 https://hinaa.ir/
curl -I --max-time 15 https://rahgard.hinaa.ir/
sudo -n nginx -t
sudo -n ss -ltn
# Review a sanitized selection of 'sudo -n nginx -T': server_name, listen, ssl_certificate, proxy_pass.
```

## Gate B — Implement a safe apex-specific deployment path

- The existing `deploy/staging/compose.yaml` derives `STAGING_PUBLIC_HOST` and `AUTH_ALLOWED_ORIGINS` from private `RAHGARD_PUBLIC_HOST`. For approved V2 cutover they must resolve to `RAHGARD_PUBLIC_HOST=hinaa.ir` and `AUTH_ALLOWED_ORIGINS=https://hinaa.ir`, while cookies remain Secure and CSRF/Host validation remains strict. No wildcard origins or unsafe cross-subdomain sharing.
- The current `deploy/staging/install-nginx-vhost.sh` is pinned to `rahgard.hinaa.ir`, rejects an occupied `:63202` listener and installs `rahgard-staging.conf`. Do not simply substitute the hostname and re-run it. Implement a distinct tested routing method based on the actual VPS topology: approved exact-SNI `server_name hinaa.ir` on a shared listener **without a second default_server**, or a separate approved HTTPS origin listener and Arvan mapping. Verify host coexistence, `nginx -t`, certificate/key match without exposing private keys, clean failure, rollback and non-interference with unrelated sites.
- Test against a **private isolated restored-data VPS rehearsal**, not the production DB. Prevent two incompatible app versions from writing to one permanent database. Enforce the existing authenticated encrypted/HMAC off-host backup and real-data 0022→0023 migration/rollback-compatibility gate first.
- Check PWA `start_url`/`scope`, service-worker and manifest paths and cache, hashed JS/CSS, proxy paths, API same-origin, authenticated traveler login/save/reopen, protected company request/plan deep links, proposal and traveler decision, company revocation, stale revision and tenant isolation.

## Gate C — Owner approval, release and exact-url acceptance

Prepare a reviewable packet naming: current occupants and conflicts, target immutable Git SHA/images, precise `hinaa.ir` DNS/Arvan/vhost/TLS changes, tested isolated restored-data migration and backup, existing-site protection, maintenance/write-freeze plan, app-and-route rollback and test accounts. **STOP and obtain separate explicit owner approval** for that frozen candidate and domain switch.

Only then activate. Required acceptance: `https://hinaa.ir/` loads V2 with valid trusted TLS and stays on apex (no redirect to `rahgard.hinaa.ir`); API, authentication cookies/CSRF, protected company links, both themes and mobile/desktop PWA work; `/`, `/sw.js`, `/manifest.webmanifest` and referenced hashed assets return 200 with correct MIME, and missing assets return 404 (old PWA 403 cannot recur). Existing other sites and all traveler/partner records remain intact. Exact Windows HEAD, GitHub commit and running VPS API/Web release SHA match. Report BLOCKED/NO-GO rather than silently substituting another URL.

**The older staging documentation and `config.env.example` still name `rahgard.hinaa.ir` because they describe the previously deployed service. Do not rewrite a running private `.env` until the owner approves the cutover.**
