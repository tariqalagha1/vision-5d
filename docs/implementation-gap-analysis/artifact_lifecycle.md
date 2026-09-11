# Artifact Lifecycle
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

### DXF (converted)

| Phase | Detail |
|-------|--------|
| **Created by** | LibreDWG (dwg2dxf.exe) during Step-01 |
| **Consumed by** | DXF Parser (Stage 2) |
| **Immutable?** | YES — once converted, never modified |
| **Regenerable?** | YES — from source DWG via LibreDWG |
| **Modifiable?** | NO |
| **Deletable?** | After pipeline completes and bundle delivered |
| **Approval gate** | SHA-256 matches Step-01 manifest |
| **Retention** | Until project archived |

### SceneGraph (.v5d)

| Phase | Detail |
|-------|--------|
| **Created by** | Scene Assembly (Stage 5), extended by Stages 6-9 |
| **Consumed by** | GLB Export, Validation, all downstream |
| **Immutable?** | YES after Stage 9 (frozen) |
| **Regenerable?** | YES — from GeometryModel + AI design |
| **Modifiable?** | During Stages 5-9 only (mesh gen, materials, lights). NO after freeze. |
| **Deletable?** | NO — authoritative record |
| **Approval gate** | SceneGraph Validation (Stage 9): zero blocking issues |
| **Retention** | PERMANENT — canonical project record |

### GLB (.glb)

| Phase | Detail |
|-------|--------|
| **Created by** | GLB Export (Stage 10) from frozen SceneGraph |
| **Consumed by** | HTML Viewer, QA, Customer |
| **Immutable?** | YES — binary export, never patched |
| **Regenerable?** | YES — re-export from same SceneGraph produces identical GLB |
| **Modifiable?** | NO — must re-export from SceneGraph if changes needed |
| **Deletable?** | Can regenerate from SceneGraph |
| **Approval gate** | GLB Validation (Stage 11): all accessors resolve, visible in viewer |
| **Retention** | Until project archived |

### HTML Viewer (index.html)

| Phase | Detail |
|-------|--------|
| **Created by** | HTML Generator (Stage 12) from GLB + camera paths |
| **Consumed by** | Browser, Video Recorder, Customer |
| **Immutable?** | YES — generated once per delivery |
| **Regenerable?** | YES — re-generate from GLB (if GLB unchanged, HTML is identical) |
| **Modifiable?** | NO — template is source, output is artifact |
| **Deletable?** | Can regenerate |
| **Approval gate** | HTML Validation (Stage 13): GLB loads, no errors |
| **Retention** | Until project archived |

### MP4 / WebM / GIF

| Phase | Detail |
|-------|--------|
| **Created by** | Video Recorder (Stage 14) from HTML (which loads GLB) |
| **Consumed by** | Customer, QA |
| **Immutable?** | YES — encoded video, never modified |
| **Regenerable?** | YES — re-record from same HTML produces content-identical video |
| **Modifiable?** | NO |
| **Deletable?** | Can regenerate (but expensive — 91s of 30fps recording) |
| **Approval gate** | Video Validation (Stage 15): non-blank frames, camera motion, GLB match |
| **Retention** | Until project archived |

### Thumbnail (thumbnail.png)

| Phase | Detail |
|-------|--------|
| **Created by** | Video Recorder (Stage 14) — first frame or best frame |
| **Consumed by** | Customer (preview) |
| **Immutable?** | YES |
| **Regenerable?** | YES |
| **Deletable?** | YES — regenerable |
| **Retention** | Until project archived |

### Validation Reports

| Phase | Detail |
|-------|--------|
| **Created by** | QA pipelines at Stages 9, 11, 13, 15 |
| **Consumed by** | Customer, Developer, Audit |
| **Immutable?** | YES — evidence, never modified |
| **Regenerable?** | NO — evidence of a specific run |
| **Modifiable?** | NO |
| **Deletable?** | NO — audit trail |
| **Retention** | PERMANENT |

### Artifact Manifest

| Phase | Detail |
|-------|--------|
| **Created by** | Bundle Assembly (Stage 16) |
| **Consumed by** | Customer, QA |
| **Immutable?** | YES — SHA-256 chain |
| **Regenerable?** | NO — specific to one bundle |
| **Modifiable?** | NO |
| **Deletable?** | NO — provenance record |
| **Retention** | PERMANENT |

---

## Lifecycle State Diagram

```
[CREATED] ──→ [VALIDATING] ──→ [APPROVED] ──→ [CONSUMED] ──→ [ARCHIVED]
                  │                    │
                  └──→ [REJECTED]      └──→ [REGENERATED] → [VALIDATING]
                       (delete,              (from upstream
                        re-create)            source)
```
