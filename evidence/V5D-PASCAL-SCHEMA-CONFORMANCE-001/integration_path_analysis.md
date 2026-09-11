# Integration Path Analysis — V5D-PASCAL-SCHEMA-CONFORMANCE-001

## Decision: CORE_FOR_TYPES_REST_FOR_SCENES_MCP_FOR_AUTOMATION

### Surface A: @pascal-app/core Imports
**Verdict: PRIMARY — use for types and schemas**

- Type safety: Full — Zod-validated at compile and runtime
- Schema reuse: Direct — import WallNode, DoorNode, etc.
- Package stability: v0.9.2 — pre-1.0 but actively maintained
- Coupling: Low — devDependency for type checking only
- Version pinning: Required — pin to 42ac4be1 commit hash

### Surface B: REST API
**Verdict: USE for scene persistence and loading**

- Validation: Zod apiGraphSchema validates every node
- Deployment: Pascal runs as separate service (Next.js)
- Persistence: SQLite via scene-store-server

### Surface C: MCP Server
**Verdict: USE for automated editing and correction capture**

- Editing: SceneOperations: createNode, updateNode, deleteNode, applyPatch
- Correction capture: All mutations are traceable via undo/redo stack

### Combined Architecture
1. V5D graph → vision5d_to_pascal_graph.ts (uses @pascal-app/core types) → SceneGraph
2. SceneGraph → POST /api/scenes → Pascal editor
3. User edits in editor → MCP mutation stream → correction events
4. Correction events → pascal_to_vision5d.ts → new V5D revision
