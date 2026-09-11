# Integration Architecture — V5D-PASCAL-BIDIRECTIONAL-INTEGRATION-001

## Module Layout
```
src/integrations/pascal/
  pascal_scene_adapter.ts      — V5D graph → Pascal scene (existing, verified)
  pascal_change_detector.ts    — Baseline vs edited scene comparison
  pascal_event_normalizer.ts   — Changes → correction events
  pascal_to_vision5d.ts        — Correction events → new V5D revision
  correction_event_validator.ts — Validation rules engine
  revision_manager.ts          — Immutable revision chain
```

## Data Flow
  1. V5D Graph → vision5d_to_pascal_adapter → Pascal Scene (baseline)
  2. Pascal Scene → user edits → Edited Pascal Scene
  3. Baseline vs Edited → pascal_change_detector → Changes
  4. Changes → pascal_event_normalizer → Correction Events
  5. Correction Events → correction_event_validator → Validated Events
  6. Validated Events → pascal_to_vision5d → New V5D Revision
  7. New V5D Revision → vision5d_to_pascal_adapter → Clean Pascal Scene
  8. Edited Pascal Scene vs Clean Pascal Scene → Round-trip verification

## Design Principles
  - Isolated module — no modification to production parser
  - No modification to Pascal core schemas
  - all changes are traceable operations
  - original V5D graph remains immutable
  - every edit produces an explicit correction event
  - deterministic scene-data comparison (not timestamp-based)
