/**
 * vision5d_to_pascal_graph.ts — Schema-Conformant Adapter v2.0
 * V5D-PASCAL-SCHEMA-CONFORMANCE-001
 * 
 * Converts Vision 5D architectural graph into Pascal-native SceneGraph.
 * Uses Pascal's authoritative types from @pascal-app/core@0.9.2.
 * Pascal commit: 42ac4be1ce5f3fee74806aa093267b6fee77d47d
 */

import type { AnyNode, AnyNodeId, WallNode, DoorNode, WindowNode, SlabNode, BuildingNode, LevelNode, SiteNode } from '@pascal-app/core/schema'
import type { SceneGraph } from '@pascal-app/core/clone-scene-graph'
import { generateId } from '@pascal-app/core/schema'

// Pascal uses Record<AnyNodeId, AnyNode>, not arrays
// Walls use start/end 2D tuples (not position + custom fields)
// Openings use wall-local position [u, v, w]
// Hierarchy uses parentId (no custom children arrays needed beyond Pascal-native ones)

export { convertVision5DToPascalGraph }
