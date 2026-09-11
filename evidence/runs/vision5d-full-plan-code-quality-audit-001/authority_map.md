# Authority Map — VISION5D-FULL-PLAN-CODE-QUALITY-AUDIT-001

Authoritative sources, in precedence order. Conflicts resolved by date + explicit supersession.

## AUTHORITATIVE (plan/design)

| # | Path | Purpose | Authority | Superseded? |
|---|------|---------|-----------|-------------|
| 1 | docs/architecture-reset/V5D-ARCHITECTURE-RESET-001.md | Single-authoritative-scene architecture; 17 stages; artifact contracts; customer delivery bundle | PRIMARY | No — the frozen architecture |
| 2 | docs/implementation-gap-analysis/implementation_gap_analysis.md | Component audit (KEEP/MODIFY/DELETE/BUILD), 7 phases, dependency graph | PRIMARY (derived from #1) | No |
| 3 | docs/implementation-gap-analysis/stage_contracts.md | Stage 0-16 contracts (executor, inputs, outputs, validation, failure mode) | PRIMARY (normative per-stage) | No |
| 4 | docs/implementation-gap-analysis/implementation_backlog.md | Phase 1-7 task breakdown + effort | PRIMARY (execution order) | No |
| 5 | README.md | Phase 1 quick start, architecture summary | SECONDARY (outdated — describes Phase 1 only) | Partially (architecture evolved to Phase 7) |

## EVIDENCE / PRIOR CERTIFICATION (supporting)

| # | Path | Purpose | Authority |
|---|------|---------|-----------|
| 6 | evidence/POST-RESET-TRUTH-RECONCILIATION-001/reconciliation_report.md | Invalidation of legacy 98.6% acceptance score; confirms GLB broken / HTML procedural / video 2D (Jul 27) | AUTHORITATIVE evidence (baseline "frozen pending approval") |
| 7 | evidence/V5D-BLENDER-RUNTIME-VERIFICATION-001/final_report.md | Blender install + GLB→Blender→FFmpeg→MP4 verified with test scene (Jul 31); 131 tests pass | AUTHORITATIVE evidence (render pipeline) |
| 8 | evidence/V5D-FULL-LOCAL-PIPELINE-WIRING-001/, V5D-BLENDER-RENDERER-INTEGRATION-001/, V5D-FULL-LOCAL-APP-INTEGRATION-001/ | Subsequent pipeline/app integration | SUPPORTING |

## CONFLICTS / UNRESOLVED

1. Architecture reset §3.2/§3.4 specifies Stage 14 = **Playwright browser recording**; actual implementation uses **Blender offline render** (packages/rendering/blender_scene_builder.py) + AI photo-tour. Deviation, not a defect — Blender render is verified working. Requires ADR (none found). UNRESOLVED deviation.
2. Architecture reset + gap analysis specify **.v5d binary format** (header/JSON/BIN/checksum); actual .v5d is **JSON (version 2.1)**. UNRESOLVED format deviation.
3. README describes "Phase 1" (17 endpoints); actual API has 105 routes across v1-v6 (Phase 7). README is stale. LOW.

No fabricated requirements. Every requirement below traces to sources #1-#4.
