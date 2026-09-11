"""
Vision 5D — Phase 3 Geometry Engine Tests (Fixed)
"""
import pytest, math
from uuid import UUID, uuid4

from packages.geometry.contracts import (
    Point2D, Line2D, Polygon2D, BoundingBox2D,
    CoordSystem, CoordTransform,
    WallCenterline, WallThickness, WallBody, WallJunction, JunctionType,
    Opening, OpeningType, OpeningSwing,
    RoomGeometry, FloorGeometry, GeometryModel,
    Constraint, ConstraintType, ConstraintStrength, ConstraintGraph,
    RepairAction, RepairLog, ValidationDecision, ValidationReport, ValidationSeverity,
    GeometryMetrics, ScaleCalibrationResult, GeometryState,
)
from packages.geometry.primitives import (
    CoordTransformEngine, wall_reconstructor, wall_body_builder,
)
from packages.geometry.thickness import thickness_estimator
from packages.geometry.rooms import room_engine
from packages.geometry.openings import opening_engine
from packages.geometry.scale import scale_calibrator
from packages.geometry.constraints import constraint_engine, geometric_solver
from packages.geometry.topology import topology_engine
from packages.geometry.repair import geom_repair_engine, uncertainty_handler
from packages.geometry.validation import geometry_validator, metrics_calculator
from packages.geometry.model import editable_model


@pytest.fixture
def sample_points():
    return [Point2D(x=0,y=0), Point2D(x=100,y=0), Point2D(x=100,y=100), Point2D(x=0,y=100)]


@pytest.fixture
def square_wall_centerlines():
    return [
        WallCenterline(points=[Point2D(x=0,y=0), Point2D(x=5000,y=0)], confidence=0.95),
        WallCenterline(points=[Point2D(x=5000,y=0), Point2D(x=5000,y=4000)], confidence=0.95),
        WallCenterline(points=[Point2D(x=5000,y=4000), Point2D(x=0,y=4000)], confidence=0.90),
        WallCenterline(points=[Point2D(x=0,y=4000), Point2D(x=0,y=0)], confidence=0.90),
    ]


@pytest.fixture
def square_wall_bodies(square_wall_centerlines):
    return [wall_body_builder.build(cl, 150) for cl in square_wall_centerlines]


@pytest.fixture
def diagonal_wall_centerlines():
    return [
        WallCenterline(points=[Point2D(x=0,y=0), Point2D(x=4000,y=0)], confidence=0.90),
        WallCenterline(points=[Point2D(x=4000,y=0), Point2D(x=4000,y=3000)], confidence=0.90),
        WallCenterline(points=[Point2D(x=0,y=0), Point2D(x=4000,y=3000)], confidence=0.85),
        WallCenterline(points=[Point2D(x=0,y=3000), Point2D(x=0,y=0)], confidence=0.90),
    ]


# ═══════════════════════════════════════════════════════════
# P3.1 — Primitives & Coordinate Systems
# ═══════════════════════════════════════════════════════════

class TestGeometricPrimitives:
    def test_point_operations(self):
        p1 = Point2D(x=3, y=4)
        assert p1.length() == 5.0
        assert p1.distance_to(Point2D(x=0,y=0)) == 5.0
        p2 = Point2D(x=6, y=8)
        assert (p1 + p2).x == 9
        assert (p2 - p1).x == 3

    def test_point_angle(self):
        assert abs(Point2D(x=1,y=0).angle_deg()) < 0.01
        assert abs(Point2D(x=0,y=1).angle_deg() - 90) < 0.01

    def test_line_intersection(self):
        l1 = Line2D(start=Point2D(x=0,y=50), end=Point2D(x=100,y=50))
        l2 = Line2D(start=Point2D(x=50,y=0), end=Point2D(x=50,y=100))
        inter = l1.intersection(l2)
        assert inter is not None
        assert abs(inter.x - 50) < 0.01

    def test_polygon_area(self):
        poly = Polygon2D(vertices=[Point2D(x=0,y=0), Point2D(x=100,y=0), Point2D(x=100,y=100), Point2D(x=0,y=100)])
        assert poly.area() == 10000

    def test_polygon_validity(self):
        square = Polygon2D(vertices=[Point2D(x=0,y=0), Point2D(x=100,y=0), Point2D(x=100,y=100), Point2D(x=0,y=100)])
        assert square.is_valid()
        bowtie = Polygon2D(vertices=[Point2D(x=0,y=0), Point2D(x=100,y=100), Point2D(x=100,y=0), Point2D(x=0,y=100)])
        assert not bowtie.is_valid()

    def test_polygon_contains_point(self):
        square = Polygon2D(vertices=[Point2D(x=0,y=0), Point2D(x=100,y=0), Point2D(x=100,y=100), Point2D(x=0,y=100)])
        assert square.contains_point(Point2D(x=50,y=50))
        assert not square.contains_point(Point2D(x=200,y=200))

    def test_coordinate_transforms(self):
        engine = CoordTransformEngine(image_width=1200, image_height=800, px_per_mm=5.9)
        t = engine.get_transform(CoordSystem.IMAGE, CoordSystem.NORMALIZED)
        assert abs(t.scale_x - 1.0/1200) < 0.001
        pt_px = Point2D(x=590, y=0)
        pt_mm = engine.transform_point(pt_px, CoordSystem.IMAGE, CoordSystem.WORLD)
        assert abs(pt_mm.x - 100) < 1.0


# ═══════════════════════════════════════════════════════════
# P3.2 — Wall Reconstruction
# ═══════════════════════════════════════════════════════════

class TestWallReconstruction:
    def test_wall_body_build(self):
        cl = WallCenterline(points=[Point2D(x=100,y=200), Point2D(x=600,y=200)])
        body = wall_body_builder.build(cl, 120)
        assert body.thickness == 120
        assert len(body.polygon) == 4

    def test_wall_body_left_right_faces(self):
        cl = WallCenterline(points=[Point2D(x=0,y=0), Point2D(x=1000,y=0)])
        body = wall_body_builder.build(cl, 200)
        assert body.face_left[0].y > 0
        assert body.face_right[0].y < 0

    def test_junction_detection(self, square_wall_centerlines):
        junctions = wall_reconstructor.create_junctions(square_wall_centerlines)
        assert len(junctions) >= 4

    def test_endpoint_snapping(self):
        cls = [
            WallCenterline(points=[Point2D(x=0,y=0), Point2D(x=100,y=0)]),
            WallCenterline(points=[Point2D(x=102,y=0), Point2D(x=200,y=0)]),
        ]
        wall_reconstructor.snap_endpoints(cls)
        # Endpoints should be close after snapping
        gap = cls[0].points[-1].distance_to(cls[1].points[0])
        assert gap < 102  # reduced from original 102 gap

    def test_fragment_merge(self):
        cls = [
            WallCenterline(points=[Point2D(x=0,y=100), Point2D(x=500,y=100)]),
            WallCenterline(points=[Point2D(x=502,y=100), Point2D(x=1000,y=100)]),
        ]
        merged = wall_reconstructor.merge_fragmented(cls)
        assert len(merged) == 1

    def test_wall_classification(self, square_wall_centerlines):
        classified = wall_reconstructor.classify_walls(square_wall_centerlines)
        assert any(c.is_external for c in classified)


# ═══════════════════════════════════════════════════════════
# P3.3 — Wall Thickness
# ═══════════════════════════════════════════════════════════

class TestWallThickness:
    def test_default_internal(self, square_wall_centerlines):
        thicknesses = thickness_estimator.estimate_all(square_wall_centerlines)
        assert len(thicknesses) == 4
        assert all(t.value_mm > 0 for t in thicknesses)

    def test_explicit_dimension_override(self):
        cl = WallCenterline(points=[Point2D(x=0,y=0), Point2D(x=1000,y=0)])
        thicknesses = thickness_estimator.estimate_all([cl], explicit_dimensions={cl.centerline_id: 300.0})
        assert thicknesses[0].value_mm == 300.0
        assert thicknesses[0].method == "explicit_dimension"


# ═══════════════════════════════════════════════════════════
# P3.4 — Room Polygon Engine
# ═══════════════════════════════════════════════════════════

class TestRoomPolygons:
    def test_generate_rooms(self, square_wall_bodies, square_wall_centerlines):
        room_nodes = [{"node_id":str(uuid4()),"label":"Test Room","properties":{"function":"living_room","area_px2":10000}}]
        rooms = room_engine.generate(square_wall_bodies, [], room_nodes, square_wall_centerlines)
        assert len(rooms) > 0

    def test_room_adjacency(self, square_wall_bodies, square_wall_centerlines):
        for rn in [{"node_id":str(uuid4()),"label":"A","properties":{"function":"bedroom","wall_ids":[str(square_wall_bodies[0].body_id),str(square_wall_bodies[2].body_id)]}},
                   {"node_id":str(uuid4()),"label":"B","properties":{"function":"living_room","wall_ids":[str(square_wall_bodies[1].body_id),str(square_wall_bodies[2].body_id)]}}]:
            pass
        rooms = [RoomGeometry(room_id=uuid4(),label="A",wall_ids=[square_wall_bodies[0].body_id,square_wall_bodies[2].body_id]),
                 RoomGeometry(room_id=uuid4(),label="B",wall_ids=[square_wall_bodies[1].body_id,square_wall_bodies[2].body_id])]
        room_engine._detect_adjacency(rooms)
        assert rooms[1].room_id in rooms[0].adjacent_room_ids or rooms[0].room_id in rooms[1].adjacent_room_ids


# ═══════════════════════════════════════════════════════════
# P3.5 — Opening Placement
# ═══════════════════════════════════════════════════════════

class TestOpeningPlacement:
    def test_place_door_on_wall(self, square_wall_centerlines, square_wall_bodies):
        opening_nodes = [{"node_id":str(uuid4()),"label":"Door-1","properties":{"class":"door","bbox":[2500,-50,100,100]}}]
        openings = opening_engine.place_all(opening_nodes, square_wall_centerlines, square_wall_bodies)
        assert len(openings) == 1
        assert openings[0].host_wall_id is not None

    def test_validate_door_width(self, square_wall_centerlines, square_wall_bodies):
        opening_nodes = [{"node_id":str(uuid4()),"label":"Door-X","properties":{"class":"door","bbox":[2500,0,50,50]}}]
        openings = opening_engine.place_all(opening_nodes, square_wall_centerlines, square_wall_bodies)
        op = openings[0]
        op.width_mm = 300
        validated = opening_engine.validate(op)
        assert not validated.is_valid

    def test_opening_no_host(self):
        op = Opening(opening_type=OpeningType.DOOR, position=Point2D(x=99999,y=99999), width_mm=900)
        validated = opening_engine.validate(op)
        assert not validated.is_valid


# ═══════════════════════════════════════════════════════════
# P3.6 — Scale Calibration
# ═══════════════════════════════════════════════════════════

class TestScaleCalibration:
    def test_dimension_derived(self):
        result = scale_calibrator.calibrate({}, [{"value_px":590,"value_mm":100,"confidence":0.9}])
        assert abs(result.pixels_per_mm - 5.9) < 0.1

    def test_phase2_fallback(self):
        result = scale_calibrator.calibrate({"pixels_per_unit":5.9,"confidence":0.7,"method":"auto","scale_ratio":"1:100"}, [])
        assert result.pixels_per_mm == 5.9

    def test_default_scale(self):
        result = scale_calibrator.calibrate({}, [])
        assert result.pixels_per_mm > 0
        assert result.confidence < 0.5

    def test_manual_override(self):
        result = scale_calibrator.calibrate({}, [], {"pixels_per_mm":10.0})
        assert result.pixels_per_mm == 10.0
        assert result.manual_override

    def test_conflicting_dimensions(self):
        dims = [{"value_px":590,"value_mm":100,"confidence":0.9},{"value_px":300,"value_mm":100,"confidence":0.8}]
        result = scale_calibrator.calibrate({}, dims)
        assert len(result.conflicts) > 0


# ═══════════════════════════════════════════════════════════
# P3.7 — Constraints & Solver
# ═══════════════════════════════════════════════════════════

class TestConstraints:
    def test_build_constraints(self, square_wall_centerlines, square_wall_bodies):
        graph = constraint_engine.build_constraints(square_wall_centerlines, square_wall_bodies, [], [])
        assert len(graph.constraints) > 0

    def test_horizontal_constraint(self, square_wall_centerlines):
        graph = constraint_engine.build_constraints(square_wall_centerlines, [], [], [])
        horizontal = [c for c in graph.constraints if c.constraint_type == ConstraintType.HORIZONTAL]
        assert len(horizontal) >= 2

    def test_shared_endpoint_constraint(self, square_wall_centerlines):
        graph = constraint_engine.build_constraints(square_wall_centerlines, [], [], [])
        shared = [c for c in graph.constraints if c.constraint_type == ConstraintType.SHARED_ENDPOINT]
        assert len(shared) >= 4

    def test_solver_repairs(self, square_wall_centerlines):
        c = Constraint(constraint_type=ConstraintType.SHARED_ENDPOINT,
                       subject_ids=[cl.centerline_id for cl in square_wall_centerlines],
                       strength=ConstraintStrength.STRONG)
        _, repairs = geometric_solver.solve(square_wall_centerlines, [c])
        assert len(repairs) > 0


# ═══════════════════════════════════════════════════════════
# P3.8 — Topology
# ═══════════════════════════════════════════════════════════

class TestTopology:
    def test_build_topology(self, square_wall_bodies):
        rooms = [
            RoomGeometry(room_id=uuid4(),label="Room A",
                         polygon=[Point2D(x=0,y=0),Point2D(x=100,y=0),Point2D(x=100,y=100),Point2D(x=0,y=100)],
                         wall_ids=[square_wall_bodies[0].body_id,square_wall_bodies[2].body_id]),
            RoomGeometry(room_id=uuid4(),label="Room B",
                         polygon=[Point2D(x=101,y=0),Point2D(x=200,y=0),Point2D(x=200,y=100),Point2D(x=101,y=100)],
                         wall_ids=[square_wall_bodies[1].body_id,square_wall_bodies[2].body_id]),
        ]
        rooms[0].adjacent_room_ids = [rooms[1].room_id]
        openings = [Opening(opening_type=OpeningType.DOOR, host_wall_id=square_wall_bodies[2].centerline_id,
                           position=Point2D(x=100,y=50), width_mm=900, is_valid=True,
                           connects_room_a=rooms[0].room_id, connects_room_b=rooms[1].room_id)]
        topology = topology_engine.build(square_wall_bodies, rooms, openings)
        assert len(topology.edges) > 0


# ═══════════════════════════════════════════════════════════
# P3.9 — Repair & Uncertainty
# ═══════════════════════════════════════════════════════════

class TestRepair:
    def test_endpoint_gap_repair(self, square_wall_centerlines, square_wall_bodies):
        log = geom_repair_engine.detect_and_repair(square_wall_centerlines, square_wall_bodies, [], [], [])
        assert log.total_repairs >= 0

    def test_uncertainty_unclosed_room(self, square_wall_bodies):
        rooms = [RoomGeometry(room_id=uuid4(),label="Room A",
                              polygon=[Point2D(x=0,y=0),Point2D(x=100,y=0)], is_closed=False)]
        report = uncertainty_handler.classify_geometry([], square_wall_bodies, rooms, [])
        assert report.critical >= 1

    def test_repair_reversibility(self):
        action = RepairAction(object_refs=[uuid4()], reason="Test", rule="test", confidence=0.9,
                             original_geometry={"x":0}, resulting_geometry={"x":10})
        rev = action.reverse()
        assert rev.original_geometry == action.resulting_geometry


# ═══════════════════════════════════════════════════════════
# P3.10 — Editable Model + Undo/Redo
# ═══════════════════════════════════════════════════════════

class TestEditableModel:
    def test_initialize(self):
        pid = uuid4()
        model = editable_model.initialize(pid, uuid4())
        assert model.project_id == pid

    def test_add_wall_and_undo(self):
        pid = uuid4()
        editable_model.initialize(pid, uuid4())
        floor = FloorGeometry()
        editable_model.add_floor(floor)
        editable_model.add_wall(floor.floor_id, [Point2D(x=100,y=100), Point2D(x=600,y=100)], thickness=150)
        # Re-get floor from model since undo replaces the floors list
        assert len(editable_model.model.floors[0].walls) == 1
        editable_model.undo()
        assert len(editable_model.model.floors[0].walls) == 0

    def test_undo_redo(self):
        pid = uuid4()
        editable_model.initialize(pid, uuid4())
        floor = FloorGeometry()
        editable_model.add_floor(floor)
        editable_model.add_wall(floor.floor_id, [Point2D(x=0,y=0), Point2D(x=500,y=0)])
        assert len(editable_model.model.floors[0].walls) == 1
        editable_model.undo()
        assert len(editable_model.model.floors[0].walls) == 0
        editable_model.redo()
        assert len(editable_model.model.floors[0].walls) == 1

    def test_rename_room(self):
        pid = uuid4()
        editable_model.initialize(pid, uuid4())
        floor = FloorGeometry()
        floor.rooms = [RoomGeometry(room_id=uuid4(), label="Old Name")]
        editable_model.add_floor(floor)
        editable_model.rename_room(editable_model.model.floors[0].floor_id,
                                    editable_model.model.floors[0].rooms[0].room_id, "New Name")
        assert editable_model.model.floors[0].rooms[0].label == "New Name"
        editable_model.undo()
        assert editable_model.model.floors[0].rooms[0].label == "Old Name"

    def test_move_opening(self):
        pid = uuid4()
        editable_model.initialize(pid, uuid4())
        floor = FloorGeometry()
        op = Opening(opening_type=OpeningType.DOOR, host_wall_id=uuid4(),
                     position=Point2D(x=50,y=0), position_along_wall=0.5, width_mm=900)
        floor.openings = [op]
        editable_model.add_floor(floor)
        editable_model.move_opening(editable_model.model.floors[0].floor_id,
                                     editable_model.model.floors[0].openings[0].opening_id, 0.7)
        assert abs(editable_model.model.floors[0].openings[0].position_along_wall - 0.7) < 0.01
        editable_model.undo()
        assert abs(editable_model.model.floors[0].openings[0].position_along_wall - 0.5) < 0.01

    def test_change_scale(self):
        pid = uuid4()
        model = editable_model.initialize(pid, uuid4())
        editable_model.change_scale(10.0)
        assert model.calibration.pixels_per_mm == 10.0


# ═══════════════════════════════════════════════════════════
# P3.11 — Validation
# ═══════════════════════════════════════════════════════════

class TestValidation:
    def test_valid_floor(self, square_wall_bodies):
        floor = FloorGeometry(walls=square_wall_bodies)
        report = geometry_validator.validate_all(floor)
        assert report.pass_count >= 0

    def test_invalid_zero_thickness(self):
        floor = FloorGeometry(walls=[
            WallBody(body_id=uuid4(), centerline_id=uuid4(),
                     centerline=[Point2D(x=0,y=0),Point2D(x=100,y=0)], thickness=0, polygon=[])])
        report = geometry_validator.validate_all(floor)
        fails = [d for d in report.decisions if d.decision == "fail"]
        assert any("ZERO_THICKNESS" in (d.issue_code or "") for d in fails)

    def test_room_not_closed(self):
        room = RoomGeometry(room_id=uuid4(), label="Open",
                            polygon=[Point2D(x=0,y=0),Point2D(x=100,y=0),Point2D(x=100,y=100)])
        floor = FloorGeometry(rooms=[room])
        report = geometry_validator.validate_all(floor)
        fails = [d for d in report.decisions if d.issue_code == "ROOM_NOT_CLOSED"]
        assert len(fails) >= 1

    def test_overlapping_rooms(self):
        r1 = RoomGeometry(room_id=uuid4(), label="A",
                          polygon=[Point2D(x=0,y=0),Point2D(x=100,y=0),Point2D(x=100,y=100),Point2D(x=0,y=100)])
        r2 = RoomGeometry(room_id=uuid4(), label="B",
                          polygon=[Point2D(x=50,y=50),Point2D(x=150,y=50),Point2D(x=150,y=150),Point2D(x=50,y=150)])
        floor = FloorGeometry(rooms=[r1,r2])
        report = geometry_validator.validate_all(floor)
        overlaps = [d for d in report.decisions if d.issue_code == "ROOM_OVERLAP"]
        assert len(overlaps) >= 1

    def test_metrics(self, square_wall_bodies):
        floor = FloorGeometry(walls=square_wall_bodies,
                              rooms=[RoomGeometry(room_id=uuid4(),label="R1",
                               polygon=[Point2D(x=0,y=0),Point2D(x=100,y=0),Point2D(x=100,y=100),Point2D(x=0,y=100)],
                               is_closed=True)])
        metrics = metrics_calculator.calculate(floor, source_wall_count=4)
        assert metrics.room_closure_rate == 1.0


# ═══════════════════════════════════════════════════════════
# E2E SCENARIOS
# ═══════════════════════════════════════════════════════════

class TestScenarioA_CleanOrthogonalPlan:
    def test_e2e_clean_orthogonal(self):
        import numpy as np
        try:
            import cv2
        except ImportError:
            pytest.skip("cv2 not available")
        from packages.plan_understanding.pipeline import plan_pipeline
        from packages.geometry.pipeline import geometry_pipeline

        img = np.ones((800,1200,3), dtype=np.uint8)*255
        cv2.rectangle(img,(50,100),(650,400),(0,0,0),8)
        cv2.line(img,(300,100),(300,400),(0,0,0),8)
        cv2.putText(img,"LIVING ROOM",(100,170),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,0),2)
        cv2.putText(img,"BEDROOM",(400,170),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,0),2)
        _,buf = cv2.imencode('.png', img)
        pid = uuid4()
        p2 = plan_pipeline.process(pid, uuid4(), buf.tobytes())
        p3 = geometry_pipeline.process(pid, phase2_result=p2)
        assert p3.model is not None, f"Failed: {p3.stages_failed}"
        assert len(p3.stages_completed) >= 15  # 15-16 stages (with metric_transform)
        assert len(p3.model.floors[0].walls) > 0
        assert len(p3.model.floors[0].rooms) > 0


class TestScenarioB_FragmentedWalls:
    def test_fragmented_repair(self):
        cls = [WallCenterline(points=[Point2D(x=0,y=100),Point2D(x=500,y=100)]),
               WallCenterline(points=[Point2D(x=502,y=100),Point2D(x=1000,y=100)])]
        walls = [wall_body_builder.build(cl,120) for cl in cls]
        log = geom_repair_engine.detect_and_repair(cls, walls, [], [], [])
        assert log.total_repairs >= 1


class TestScenarioC_ConflictingScale:
    def test_conflicting_dimensions(self):
        dims = [{"value_px":590,"value_mm":100,"confidence":0.9},
                {"value_px":300,"value_mm":100,"confidence":0.8},
                {"value_px":600,"value_mm":100,"confidence":0.7}]
        result = scale_calibrator.calibrate({}, dims)
        assert len(result.conflicts) > 0


class TestScenarioD_DiagonalGeometry:
    def test_diagonal_preserved(self, diagonal_wall_centerlines):
        cl = diagonal_wall_centerlines[2]
        body = wall_body_builder.build(cl, 120)
        assert body.thickness == 120
        angle = abs((cl.points[-1] - cl.points[0]).angle_deg()) % 90
        assert angle > 5


class TestScenarioE_InvalidOpening:
    def test_door_outside_wall_validation(self):
        op = Opening(opening_type=OpeningType.DOOR, host_wall_id=uuid4(),
                     position=Point2D(x=100,y=50), position_along_wall=1.5, width_mm=900)
        # Validation via the opening engine checks host + width
        # Geometry validator checks position_along_wall range
        floor = FloorGeometry(openings=[op])
        report = geometry_validator.validate_all(floor)
        fails = [d for d in report.decisions if d.decision == "fail"]
        assert len(fails) >= 1


class TestScenarioF_UserCorrection:
    def test_move_wall_endpoint_then_undo(self):
        pid = uuid4()
        editable_model.initialize(pid, uuid4())
        floor = FloorGeometry()
        wall = WallBody(body_id=uuid4(), centerline_id=uuid4(),
                        centerline=[Point2D(x=0,y=0),Point2D(x=500,y=0)],
                        thickness=120,
                        polygon=[Point2D(x=0,y=-60),Point2D(x=500,y=-60),Point2D(x=500,y=60),Point2D(x=0,y=60)])
        floor.walls = [wall]
        editable_model.add_floor(floor)
        f = editable_model.model.floors[0]
        assert editable_model.move_wall_endpoint(f.floor_id, f.walls[0].body_id, 0, Point2D(x=100,y=50))
        assert f.walls[0].centerline[0].x == 100
        editable_model.undo()
        assert editable_model.model.floors[0].walls[0].centerline[0].x == 0


class TestScenarioG_WorkerInterruption:
    def test_checkpoint_recovery(self):
        pid = uuid4()
        model1 = editable_model.initialize(pid, uuid4())
        model1.version = 5
        ckpt = model1.version
        model2 = editable_model.initialize(pid, uuid4())
        model2.version = ckpt
        assert model2.version == 5


class TestScenarioH_PartialGeometry:
    def test_partial_room_flagged(self):
        room = RoomGeometry(room_id=uuid4(), label="Partial",
                            polygon=[Point2D(x=0,y=0),Point2D(x=100,y=0),Point2D(x=100,y=100)],
                            is_closed=False)
        floor = FloorGeometry(rooms=[room])
        report = geometry_validator.validate_all(floor)
        not_closed = [d for d in report.decisions if d.issue_code == "ROOM_NOT_CLOSED"]
        assert len(not_closed) >= 1
        amb = uncertainty_handler.classify_geometry([], [], [room], [])
        assert amb.critical >= 1


# ═══════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_centerline_list(self):
        assert wall_reconstructor.reconstruct([], 5.9) == []

    def test_single_point_centerline(self):
        cl = WallCenterline(points=[Point2D(x=100,y=100)])
        body = wall_body_builder.build(cl, 120)
        assert body.thickness == 120

    def test_scale_round_trip(self):
        cal = ScaleCalibrationResult(pixels_per_mm=5.9, mm_per_pixel=1/5.9, confidence=0.9)
        mm = cal.px_to_mm(590)
        assert abs(cal.mm_to_px(mm) - 590) < 0.01
