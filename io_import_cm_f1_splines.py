bl_info = {
    "name": "CM F1 Spline Importer",
    "author": "haunetal1990",
    "version": (0, 8),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar (N-Panel) > CM F1",
    "description": "Imports Track, AI, TrackSpace splines, and cameras (searches recursively in subfolders)",
    "category": "Import-Export",
}

import bpy
import re
from pathlib import Path
from mathutils import Vector
from collections import defaultdict

# ====================================================
# Global Constants & Helper Functions
# ====================================================
DISTANCE_LIMIT = 150.0

def get_or_create_collection(name, parent_collection=None):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
        
    col = bpy.data.collections.new(name)
    if parent_collection is None:
        bpy.context.scene.collection.children.link(col)
    else:
        parent_collection.children.link(col)
    return col

def split_into_segments(points, distance_limit):
    if not points:
        return []
    segments = []
    current  = [points[0]]
    for i in range(1, len(points)):
        if (points[i] - points[i - 1]).length > distance_limit:
            segments.append(current)
            current = [points[i]]
        else:
            current.append(points[i])
    if current:
        segments.append(current)
    return segments

def make_curve_object(obj_name, segment, distance_limit, collection, make_rounder=False):
    if len(segment) < 2:
        return None
    if obj_name in bpy.data.objects:
        old_obj = bpy.data.objects[obj_name]
        if old_obj.data:
            bpy.data.curves.remove(old_obj.data)
        else:
            bpy.data.objects.remove(old_obj)
            
    curve = bpy.data.curves.new(obj_name, "CURVE")
    curve.dimensions = '3D'
    
    if make_rounder:
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(len(segment) - 1)
        for i, p in enumerate(segment):
            bp = spline.bezier_points[i]
            bp.co = (p.x, p.y, p.z)
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
    else:
        spline = curve.splines.new("POLY")
        spline.points.add(len(segment) - 1)
        for i, p in enumerate(segment):
            spline.points[i].co = (p.x, p.y, p.z, 1)
            
    if (segment[0] - segment[-1]).length < distance_limit:
        spline.use_cyclic_u = True
        
    obj = bpy.data.objects.new(obj_name, curve)
    collection.objects.link(obj)
    return obj

def bfloat(b):
    return float(b.decode("ascii"))

def to_blender(x, y, z):
    # Convert F1 coordinates to Blender (swapping Y and Z, inverting Z)
    return Vector((x, -z, y))

def deduplicate_points(points, threshold=0.1):
    if not points:
        return []
    result = [points[0]]
    for p in points[1:]:
        if (p - result[-1]).length > threshold:
            result.append(p)
    return result

def extract_points(filepath):
    try:
        with open(filepath, 'rb') as f:
            raw_bytes = f.read()
            
        # Replace null bytes (binary padding) with spaces and decode
        text = raw_bytes.replace(b'\x00', b' ').decode('ascii', errors='ignore')
        
        # Regex to filter coordinates
        pattern = r'position[^\d-]*([-\d.eE]+)\s*,\s*([-\d.eE]+)\s*,\s*([-\d.eE]+)'
        
        points = []
        for match in re.findall(pattern, text, re.IGNORECASE):
            points.append(to_blender(float(match[0]), float(match[1]), float(match[2])))
            
        return points
    except Exception as e:
        print(f"Error reading file {filepath.name}: {e}")
        return []

# ====================================================
# Operator (Main Import Logic)
# ====================================================
class CMF1_OT_ImportSplines(bpy.types.Operator):
    bl_idname = "import_scene.cm_f1_splines"
    bl_label = "Import"
    bl_description = "Starts importing spline and camera files from the selected folder"

    def execute(self, context):
        props = context.scene.cm_f1_props
        folder_str = props.folder_path
        make_rounder = props.make_rounder

        if not folder_str.strip():
            self.report({'ERROR'}, "Error: No folder path specified!")
            return {'CANCELLED'}

        FOLDER = Path(bpy.path.abspath(folder_str))
        if not FOLDER.exists() or not FOLDER.is_dir():
            self.report({'ERROR'}, f"Error: Folder does not exist: {FOLDER}")
            return {'CANCELLED'}

        try:
            track_file = next(FOLDER.rglob("*.trackspacespline*"))
            ai_file    = next(FOLDER.rglob("*.aispline*"))
            ts_file    = next(FOLDER.rglob("*.trackspacedata*"))
        except StopIteration:
            self.report({'ERROR'}, "Error: Could not find all 3 required spline files (even in subfolders)!")
            return {'CANCELLED'}

        # --- Determine track name from file name ---
        file_name = track_file.name.lower()
        if "_ai_track" in file_name:
            raw_name = file_name.split("_ai_track")[0]
        else:
            raw_name = file_name.split("_")[0]
        
        track_name = raw_name.replace("_", " ").title()
        prefix = raw_name.replace("_", " ").title().replace(" ", "_")

        print("\n=== CM F1 Spline Import Started ===")
        print(f"Track detected:  {track_name} (Prefix: {prefix})")
        print("Track File:      ", track_file)
        print("AI File:         ", ai_file)
        print("TrackSpace File: ", ts_file)

        # --- Create Collections ---
        col_master = get_or_create_collection(track_name)
        col_track = get_or_create_collection(f"{prefix}_Track", parent_collection=col_master)
        col_ai    = get_or_create_collection(f"{prefix}_AI_Splines", parent_collection=col_master)
        col_ts    = get_or_create_collection(f"{prefix}_TrackSpace", parent_collection=col_master)

        # ----------------- READ TRACK -----------------
        with open(track_file, "rb") as f:
            track = f.read().decode("latin1", errors="ignore")
        track_points = []
        for x, y, z in re.findall(r'position\x00([-\d.eE]+),\s*([-\d.eE]+),\s*([-\d.eE]+)', track):
            track_points.append(Vector((float(x), -float(z), float(y))))
        
        if track_points:
            track_segments = split_into_segments(track_points, DISTANCE_LIMIT)
            track_segments.sort(key=len, reverse=True)
            label_map = {0: "Track_Main", 1: "Track_Pitlane"}
            for idx, seg in enumerate(track_segments):
                obj_name = f"{prefix}_" + label_map.get(idx, f"Track_Extra_{idx}")
                make_curve_object(obj_name, seg, DISTANCE_LIMIT, col_track, make_rounder)

        # ----------------- READ AI -----------------
        with open(ai_file, "rb") as f:
            ai = f.read().decode("latin1", errors="ignore")
        gate_pattern = re.compile(
            r'position\x00x\x00([-\d.eE]+)\x00'
            r'y\x00([-\d.eE]+)\x00'
            r'z\x00([-\d.eE]+).*?'
            r'normal\x00x\x00([-\d.eE]+)\x00'
            r'y\x00([-\d.eE]+)\x00'
            r'z\x00([-\d.eE]+)(.*?)'
            r'(?=position\x00x\x00|\Z)',
            re.S
        )
        gates = []
        for match in gate_pattern.finditer(ai):
            px, py, pz = map(float, match.group(1, 2, 3))
            nx, ny, nz = map(float, match.group(4, 5, 6))
            waypoints  = {}
            for wp in re.finditer(r'type\x00([^\x00]+)\x00length\x00([-\d.eE]+)', match.group(7)):
                waypoints[wp.group(1)] = float(wp.group(2))
            gates.append({"position": Vector((px, py, pz)), "normal": Vector((nx, ny, nz)), "waypoints": waypoints})
            
        types = set()
        for g in gates:
            types.update(g["waypoints"].keys())
        spline_points = {t: [] for t in types}
        
        for g in gates:
            pos    = g["position"]
            normal = g["normal"]
            for name, length in g["waypoints"].items():
                raw   = pos + normal * length
                point = Vector((raw.x, -raw.z, raw.y))
                spline_points[name].append(point)
                
        for spline_name, pts in spline_points.items():
            if len(pts) < 2: continue
            segments = split_into_segments(pts, DISTANCE_LIMIT)
            segments.sort(key=len, reverse=True)
            label_map = {0: "Main", 1: "Pit"}
            for idx, seg in enumerate(segments):
                suffix   = label_map.get(idx, f"Extra_{idx}")
                obj_name = f"{prefix}_AI_{spline_name}_{suffix}"
                make_curve_object(obj_name, seg, DISTANCE_LIMIT, col_ai, make_rounder)

        # ----------------- READ TRACKSPACE DATA -----------------
        with open(ts_file, "rb") as f:
            ts_raw_bytes = f.read()
        NUM_B = rb'[-+]?\d+\.\d+(?:[eE][-+]?\d+)?'
        def xyz_groups():
            return (rb'(' + NUM_B + rb'),\s*'
                    rb'(' + NUM_B + rb'),\s*'
                    rb'(' + NUM_B + rb')')
        NOT_POINT = rb'[^p]*(?:p(?!oint)[^p]*)*'
        gate_pattern_ts = re.compile(
            rb'point1\x00' + xyz_groups() + NOT_POINT +
            rb'point2\x00' + xyz_groups() + NOT_POINT +
            rb'point3\x00' + xyz_groups() + NOT_POINT +
            rb'point4\x00' + xyz_groups(), re.S)
            
        all_gate_matches = list(gate_pattern_ts.finditer(ts_raw_bytes))
        vl_positions = [m.start() for m in re.finditer(rb'VolumeList', ts_raw_bytes)]
        type_pattern_b = re.compile(rb'type\x00(\w+)')
        ts_data_by_type = {}
        
        for i, vl_start in enumerate(vl_positions):
            vl_end = vl_positions[i+1] if i+1 < len(vl_positions) else len(ts_raw_bytes)
            block  = ts_raw_bytes[vl_start:vl_end]
            type_m = type_pattern_b.search(block)
            if not type_m: continue
            vol_type = type_m.group(1).decode("ascii").lower()
            centers = []
            for gm in gate_pattern_ts.finditer(block):
                try:
                    x1,y1,z1 = bfloat(gm.group(1)), bfloat(gm.group(2)), bfloat(gm.group(3))
                    x2,y2,z2 = bfloat(gm.group(4)), bfloat(gm.group(5)), bfloat(gm.group(6))
                    x3,y3,z3 = bfloat(gm.group(7)), bfloat(gm.group(8)), bfloat(gm.group(9))
                    x4,y4,z4 = bfloat(gm.group(10)), bfloat(gm.group(11)), bfloat(gm.group(12))
                    cx, cy, cz = (x1+x2+x3+x4)/4.0, (y1+y2+y3+y4)/4.0, (z1+z2+z3+z4)/4.0
                    centers.append(to_blender(cx, cy, cz))
                except: continue
            if centers:
                ts_data_by_type.setdefault(vol_type, []).extend(centers)
                
        if not ts_data_by_type and all_gate_matches:
            centers = []
            for gm in all_gate_matches:
                try:
                    x1,y1,z1 = bfloat(gm.group(1)), bfloat(gm.group(2)), bfloat(gm.group(3))
                    x2,y2,z2 = bfloat(gm.group(4)), bfloat(gm.group(5)), bfloat(gm.group(6))
                    x3,y3,z3 = bfloat(gm.group(7)), bfloat(gm.group(8)), bfloat(gm.group(9))
                    x4,y4,z4 = bfloat(gm.group(10)), bfloat(gm.group(11)), bfloat(gm.group(12))
                    cx, cy, cz = (x1+x2+x3+x4)/4.0, (y1+y2+y3+y4)/4.0, (z1+z2+z3+z4)/4.0
                    centers.append(to_blender(cx, cy, cz))
                except: continue
            if centers:
                ts_data_by_type["main"] = centers
                
        ts_label_map = {"main": "TS_Main", "pit": "TS_Pit"}
        for ts_type, pts in ts_data_by_type.items():
            pts_clean = deduplicate_points(pts)
            if len(pts_clean) < 2: continue
            
            col_ts_sub = get_or_create_collection(f"{prefix}_TrackSpace_{ts_type.capitalize()}", col_ts)
            segments = split_into_segments(pts_clean, DISTANCE_LIMIT)
            segments.sort(key=len, reverse=True)
            base_name = ts_label_map.get(ts_type, f"TS_{ts_type.capitalize()}")
            for idx, seg in enumerate(segments):
                obj_name = f"{prefix}_" + (base_name if idx == 0 else f"{base_name}_Extra_{idx}")
                make_curve_object(obj_name, seg, DISTANCE_LIMIT, col_ts_sub, make_rounder)

        # ----------------- READ CAMERAS -----------------
        print("\n--- Searching for Camera Splines ---")
        cam_files = defaultdict(lambda: {'cam': None, 'target': None})
        
        for f in FOLDER.rglob("*.spline*"):
            if not f.is_file(): continue
            name = f.name.lower()
            if "_cam_target" in name:
                cam_files[name.replace("_cam_target", "")]['target'] = f
            elif "_cam" in name:
                cam_files[name.replace("_cam", "")]['cam'] = f
                
        if cam_files:
            col_cams = get_or_create_collection(f"{prefix}_Cameras", parent_collection=col_master)
            cam_count = 0
            
            for key, paths in cam_files.items():
                if not paths['cam']: continue
                
                clean_key = key.split('.')[0].replace('!!!', '_')
                cam_points = extract_points(paths['cam'])
                
                target_points = []
                if paths['target']:
                    target_points = extract_points(paths['target'])
                    
                if not cam_points:
                    continue
                    
                for i, pos in enumerate(cam_points):
                    cam_name = f"{prefix}_Cam_{clean_key}_{i+1:02d}"
                    
                    if cam_name in bpy.data.objects:
                        bpy.data.objects.remove(bpy.data.objects[cam_name], do_unlink=True)
                        
                    cam_data = bpy.data.cameras.new(name=cam_name)
                    cam_obj = bpy.data.objects.new(cam_name, cam_data)
                    cam_obj.location = pos
                    col_cams.objects.link(cam_obj)
                    cam_count += 1
                    
                    # Target Empty & Constraint setup
                    if i < len(target_points):
                        target_name = f"{cam_name}_Target"
                        if target_name in bpy.data.objects:
                            bpy.data.objects.remove(bpy.data.objects[target_name], do_unlink=True)
                            
                        target_obj = bpy.data.objects.new(target_name, None)
                        target_obj.location = target_points[i]
                        target_obj.empty_display_type = 'SPHERE'
                        target_obj.empty_display_size = 2.0
                        col_cams.objects.link(target_obj)
                        
                        constraint = cam_obj.constraints.new(type='TRACK_TO')
                        constraint.target = target_obj
                        constraint.track_axis = 'TRACK_NEGATIVE_Z'
                        constraint.up_axis = 'UP_Y'
                        
            print(f"Successfully imported {cam_count} cameras into '{prefix}_Cameras' collection.")

        self.report({'INFO'}, f"CM F1 splines and cameras for '{track_name}' successfully imported!")
        return {'FINISHED'}

# ====================================================
# UI Elements (Properties & Panel)
# ====================================================
class CMF1_Properties(bpy.types.PropertyGroup):
    folder_path: bpy.props.StringProperty(
        name="Folder",
        description="Select the folder where the spline files are located",
        default="",
        subtype='DIR_PATH'
    )
    make_rounder: bpy.props.BoolProperty(
        name="Rounder Roads",
        description="Smooths out curves (uses Bezier Splines instead of hard Polylines)",
        default=False
    )

class CMF1_PT_Panel(bpy.types.Panel):
    bl_label = "CM F1 Importer"
    bl_idname = "CMF1_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CM F1'

    def draw(self, context):
        layout = self.layout
        props = context.scene.cm_f1_props
        layout.prop(props, "folder_path")
        layout.prop(props, "make_rounder")
        layout.separator()
        layout.operator("import_scene.cm_f1_splines", icon='IMPORT')

# ====================================================
# Registration
# ====================================================
classes = (
    CMF1_Properties,
    CMF1_OT_ImportSplines,
    CMF1_PT_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cm_f1_props = bpy.props.PointerProperty(type=CMF1_Properties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.cm_f1_props

if __name__ == "__main__":
    register()
