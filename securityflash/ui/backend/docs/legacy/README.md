# LEGACY CODE - DO NOT USE

These files are from V2's original architecture where it had its own database.

**V2 is now a stateless BFF (Backend-For-Frontend) that ONLY proxies to SecurityFlash V1.**

SecurityFlash V1 is the single source of truth for:
- Projects, Scopes, Runs, Actions
- Approvals, Evidence, Findings
- Audit logs, Users, Permissions

DO NOT re-enable these files. If V2 needs data, it must proxy to V1.

