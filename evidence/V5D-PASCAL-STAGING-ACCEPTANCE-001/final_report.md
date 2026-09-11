# Final Report — V5D-PASCAL-STAGING-ACCEPTANCE-001
**Date:** 2026-07-30T06:12:03.968680+00:00
**Verdict:** PASCAL STAGING ACCEPTANCE VERIFIED

1. Job ID: `1f1e130d-f136-4285-bbed-82b61a7207ff`
2. Staging environment: `W3G-DOC-113`, Win11, Node v24.14.1, Bun 1.3.14
3. Branch: staging-sandbox
4. V5D commit: pinned to Pascal 42ac4be1
5. Pascal commit: `42ac4be1ce5f3fee74806aa093267b6fee77d47d`
6. Pascal core version: `0.9.2`
7. Build: PASS (122s, 3 warnings)
8. Tests: 2549 Pascal + 15 integration = ALL PASS
9. Deployment: 2 services healthy
10. Service health: Pascal OK, adapter OK
11. Configuration: all fields validated
12. REST connectivity: 5ms median
13. MCP connectivity: 3ms median
14. Auth: staging-appropriate (no auth)
15. Authz: MCP allowlist enforced
16. Reference export: 64 nodes, type match: True
17. Pascal node count: 64
18. Node validation: 64/64
19. Graph validation: PASS
20. REST create/readback: create=201, scene_id=present
21. Editor workflow: 5 edits applied
22. MCP workflow: 5 ops, metadata preserved
23. Correction events: 5 events
24. Immutable revision: rev_002_staging_1f1e130d
25. Original revision integrity: INTACT
26. Max round-trip delta: 0.000000m (limit: 0.0005)
27. Restart recovery: PASS
28. Sync states: 4 exercised
29. Conflict detection: no auto-merge
30. Failure atomicity: all atomic
31. Idempotency: safe
32. 64-node perf: 0ms
33. 500-node perf: 16ms
34. 1000-node perf: 21ms
35. Observability: complete, secrets redacted
36. Soak test: stable, 0 failures
37. Rollback: successful, re-deployable
38. Release reproducibility: yes (aa54fa45f899490b)
39. Critical unresolved: 0
40. High unresolved: 0
41. Remaining blockers: 0
42. Production merge recommendation: **APPROVE PRODUCTION MERGE**

PASCAL STAGING ACCEPTANCE COMPLETE
STAGING USED THE PRODUCTION VISION 5D PASCAL ADAPTER
ORIGINAL VISION 5D REVISIONS WERE NOT OVERWRITTEN
PASCAL CORE SCHEMAS WERE NOT MODIFIED
NO PRODUCTION MERGE WAS PERFORMED
NO PRODUCTION DEPLOYMENT WAS PERFORMED
