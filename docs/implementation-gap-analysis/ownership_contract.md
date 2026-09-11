# Ownership Contracts
## V5D-IMPLEMENTATION-GAP-ANALYSIS-001

**Principle**: Every data structure has EXACTLY ONE owner. No shared ownership. No dual authority.

---

## Primary Owner: SceneGraph (.v5d)

The SceneGraph is the SOLE AUTHORITATIVE OWNER of all scene data. Every downstream artifact is a READ-ONLY derivative.

### Walls

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph → BuildingLevel.walls[] → WallSolid |
| **Created by** | Scene Assembly (Stage 5) |
| **Source trace** | WallSolid.solid_id → GeometryWall.centerline_id → ArchGraph wall node → CAD LINE entity |
| **Consumer 1** | Mesh Generator — converts to MeshData |
| **Consumer 2** | GLB Export — writes as glTF node/mesh |
| **Never owned by** | HTML, Video, JSON file, GeometryModel (that's the INPUT, not the authoritative scene) |

### Doors

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph → BuildingLevel.doors[] → DoorElement |
| **Created by** | Scene Assembly (Stage 5) |
| **Source trace** | DoorElement.source_opening_id → GeometryOpening.id → ArchGraph opening node → CAD ARC/LINE |
| **Consumer** | GLB Export |

### Windows

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph → BuildingLevel.windows[] → WindowElement |
| **Created by** | Scene Assembly (Stage 5) |
| **Source trace** | WindowElement.source_opening_id → GeometryOpening.id |
| **Consumer** | GLB Export |

### Rooms

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph → BuildingLevel.rooms[] → RoomVolume |
| **Created by** | Scene Assembly (Stage 5) |
| **Source trace** | RoomVolume.source_room_id → GeometryRoom.id → ArchGraph room node |
| **Consumer** | Mesh Generator (floor/ceiling from room polygon) |

### Furniture

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph → BuildingLevel.furniture_instances[] → FurnitureInstance |
| **Created by** | AI Design → Scene Assembly (Stage 6→5) |
| **MUTABLE?** | Yes — position, rotation, scale, color_override editable in studio UNTIL scene frozen |
| **After freeze** | Immutable |
| **Consumer** | GLB Export (as glTF nodes with transform) |

### Materials

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph.materials[] → Material |
| **Created by** | Material Assignment (Stage 7) |
| **MUTABLE?** | Yes — baseColor, roughness, metallic, texture_ref editable UNTIL frozen |
| **Consumer** | GLB Export (as glTF materials array) |

### Textures

| Property | Value |
|----------|-------|
| **Owner** | Material.texture_ref (reference to external file) |
| **Storage** | External image files (PNG/JPG) in project assets/ |
| **Consumer** | GLB Export (embeds or references texture URIs) |

### Lights

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph.lights[] → SceneLight |
| **Created by** | Lighting Setup (Stage 8) |
| **Consumer** | GLB Export (KHR_lights_punctual extension) |

### Cameras

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph.cameras[] → Camera |
| **Created by** | Scene Assembly (Stage 5), extended by Cinematic Director |
| **Consumer** | HTML Viewer (initial view), Video Recorder (camera paths) |

### Meshes

| Property | Value |
|----------|-------|
| **Owner** | SceneGraph.building.levels[].meshes[] → MeshData |
| **Created by** | Mesh Generator (Stage 6) |
| **IMMUTABLE** | Yes — vertices, indices, normals are generated once |
| **Consumer** | GLB Export (primary geometry data) |

---

## Secondary Owners

### Validation Results

| Property | Value |
|----------|-------|
| **Owner** | QA Pipeline (read-only agent) |
| **Created by** | Stage validators (11, 13, 15) |
| **IMMUTABLE** | Yes — evidence, never modified |
| **Consumer** | Bundle Assembly (included in delivery) |

### Job State

| Property | Value |
|----------|-------|
| **Owner** | SQLAlchemy Domain DB |
| **Created by** | Worker (17-state machine) |
| **Consumer** | API endpoints, Worker |

### Artifact Manifest

| Property | Value |
|----------|-------|
| **Owner** | Bundle Assembly (Stage 16) |
| **Created by** | Artifact manifest system |
| **IMMUTABLE** | Yes — SHA-256 chain |
| **Consumer** | QA, Customer |

---

## Cross-Ownership Conflicts (NONE)

No data structure is owned by two components. The SceneGraph OWNS scene data. Everything else READS it.

```
GeometryModel ──(input to)──→ SceneGraph ──(output from)──→ GLB
                                     │
JSON file is INPUT                     │
NOT the authority                     └── SceneGraph IS the authority
```
