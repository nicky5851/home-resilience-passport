# Team decisions

Append-only. One line per team-level decision or shared-file change (spec §3.3, §13).
Coder-level decisions live in `docs/decisions/N.md` and `docs/decisions/L.md`; entries marked
"Affects the other coder? yes" are copied here at the next sync meeting.

| Date | Who | What | Why |
| --- | --- | --- | --- |
| 2026-10-26 | N, L | Spec v1.3 and `CONTRACT.md` (contract-v1 draft) adopted | Foundation plan |
| 2026-10-27 | Owner | M2a moves to after submission (from Mon 16 Nov) | Less pressure in freeze week (spec §15) |
| 2026-10-27 | Owner (N) | CONTRACT §2 hot-day threshold 30 °C → 28 °C | Hot-day check: EC_Earth3P_HR gives 0.83 days/yr ≥ 30 °C in London 1991–2020 (2.33 at 28 °C) |
| 2026-10-27 | N (L agreed) | EPC register API: base URL is the `EPC_API_BASE_URL` setting (live `https://api.get-energy-performance-data.communities.gov.uk` by default; integration tokens need `https://api.get-energy-performance-data.epb-integration.communities.gov.uk`), header `Authorization: Bearer <EPC_API_TOKEN>` (token from the service's "my account" page), `Accept: application/json`; limit 6000 requests / 5 min | Spec N6: record base URL and auth; a token only works on the environment that issued it |
