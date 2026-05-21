"""Enums for MapIR. All string-valued so JSON round-trips cleanly."""

from __future__ import annotations

from enum import Enum


class IRType(str, Enum):
    WORLD = "world"
    SCENE = "scene"


# ---------- World ----------

class Density(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class HeightProfile(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    MIXED = "mixed"


class RoadType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ALLEY = "alley"
    SERVICE = "service"
    PATH = "path"


class WaterType(str, Enum):
    RIVER = "river"
    CANAL = "canal"
    SEA = "sea"
    LAKE = "lake"
    POND = "pond"
    HARBOR = "harbor"


# ---------- Scene ----------

class SceneType(str, Enum):
    EXTERIOR_LOCATION = "exterior_location"
    INTERIOR = "interior"


class ScenePreset(str, Enum):
    URBAN_ALLEY = "urban_alley"
    WAREHOUSE_INTERIOR = "warehouse_interior"
    PORT_YARD = "port_yard"
    CUSTOM = "custom"


class ZoneType(str, Enum):
    PATH = "path"
    COMBAT_SPACE = "combat_space"
    STEALTH_ROUTE = "stealth_route"
    SERVICE_AREA = "service_area"
    PUBLIC_AREA = "public_area"
    PRIVATE_AREA = "private_area"
    ROOM = "room"
    STORAGE = "storage"
    EXTERIOR_YARD = "exterior_yard"
    DANGER_ZONE = "danger_zone"
    SAFE_ZONE = "safe_zone"


class EntranceType(str, Enum):
    MAIN = "main"
    SIDE = "side"
    BACKDOOR = "backdoor"
    EMERGENCY = "emergency"
    SERVICE = "service"
    ROOF = "roof"
    HIDDEN = "hidden"


class ScenePathType(str, Enum):
    MAIN_ROUTE = "main_route"
    ALTERNATE_ROUTE = "alternate_route"
    STEALTH_ROUTE = "stealth_route"
    ESCAPE_ROUTE = "escape_route"
    PATROL_ROUTE = "patrol_route"


class SceneObjectType(str, Enum):
    WALL = "wall"
    BUILDING_BLOCK = "building_block"
    PROP = "prop"
    COVER = "cover"
    CONTAINER = "container"
    FURNITURE = "furniture"
    DOOR = "door"
    WINDOW = "window"
    STAIRS = "stairs"
    MARKER = "marker"
    LIGHT = "light"


class MarkerType(str, Enum):
    COVER = "cover"
    AMBUSH = "ambush"
    OBJECTIVE = "objective"
    ENEMY_SPAWN = "enemy_spawn"
    PLAYER_SPAWN = "player_spawn"
    INTERACTION = "interaction"
    CLIMB = "climb"
    VAULT = "vault"
    HIDING_SPOT = "hiding_spot"
    EXTRACTION = "extraction"
    CAMERA_FOCUS = "camera_focus"


# ---------- Assets ----------

class AssetCategory(str, Enum):
    BUILDING = "building"
    PROP = "prop"
    VEGETATION = "vegetation"
    ROAD_PIECE = "road_piece"
    WALL = "wall"
    BRIDGE = "bridge"
    LANDMARK = "landmark"
    FURNITURE = "furniture"
    CONTAINER = "container"
    DOOR = "door"
    WINDOW = "window"
    STAIRS = "stairs"
    LIGHT = "light"


class Collision(str, Enum):
    NONE = "none"
    SIMPLE = "simple"
    COMPLEX = "complex"


# ---------- Constraints ----------

class ConstraintType(str, Enum):
    MUST_HAVE_MIN_ENTRANCES = "must_have_min_entrances"
    MUST_HAVE_MIN_ESCAPE_ROUTES = "must_have_min_escape_routes"
    MUST_HAVE_MIN_COVER_MARKERS = "must_have_min_cover_markers"
    MUST_HAVE_SCENE_SLOT = "must_have_scene_slot"
    MUST_BE_ADJACENT = "must_be_adjacent"
    MUST_NOT_OVERLAP = "must_not_overlap"
    MUST_CONNECT_TO_ROAD = "must_connect_to_road"
    MUST_BE_INSIDE_BOUNDS = "must_be_inside_bounds"
    CUSTOM = "custom"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
