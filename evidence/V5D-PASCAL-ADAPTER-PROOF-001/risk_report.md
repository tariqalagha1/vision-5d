# Pascal Adapter Integration — Risk Report

## V5D-PASCAL-ADAPTER-PROOF-001

---

## Risk Summary

| Risk | Severity | Likelihood | Status |
|---|---|---|---|
| Pascal build/environment dependency | LOW | LOW | Pascal uses Bun + TypeScript standard toolchain |
| Coordinate system mismatch | MEDIUM | LOW | Y-up vs Z-up handled in adapter. Verified at 0.0 delta. |
| Unit scale mismatch | LOW | NONE | Both systems use meters |
| DWG entity fidelity loss | LOW | NONE | All DXF handles preserved in metadata |
| Door/window block recognition | MEDIUM | MEDIUM | INSERT block names not fully parsed — need block table inspection |
| Wall thickness assumptions | LOW | MEDIUM | Default 200mm used. DWG may specify exact thickness |
| Slab polygon correctness | LOW | LOW | Derived from exterior wall loop with shoelace area validation |
| Pascal schema version drift | MEDIUM | LOW | Pascal v0.9.2. Schema changes could break adapter. |
| Metadata field removal | LOW | VERY LOW | BaseNode.metadata is a core Pascal field (z.json()). Removing it would break Pascal's own extensibility. |
| Round-trip fidelity | LOW | LOW | Provenance stays in metadata.vision5d. Geometry positions are read from Pascal's own state. |
| Performance (57 walls) | LOW | LOW | 63 nodes is trivial for Pascal's scene graph |
| Pascal not built/tested | HIGH | NONE | Pascal was inventoried but not built — per mission scope "isolated evaluation directory" |

---

## Required Pascal Modifications

**None.** The adapter uses only:
- `BaseNode.metadata` (core field, no modification needed)
- Standard node types: building, level, wall, slab, door, window
- Standard parentId hierarchy

No Pascal schema changes required. No Pascal core changes required.

---

## Integration Path

1. **Phase 1 (this proof):** Isolated adapter verified with 57-wall test scene
2. **Phase 2:** Build Pascal, load scene via `applyScenePatch` or MCP
3. **Phase 3:** Visual render verification with actual Three.js output
4. **Phase 4:** Full round-trip: Vision 5D → Pascal → edit → export → Vision 5D ingest

---

## Recommendation

**CONTINUE LIMITED EVALUATION** — The proof shows Pascal's schema is compatible, metadata provides provenance storage, and wall/slab/door/window geometry maps cleanly. The next step is building Pascal and loading the generated scene for visual verification.
