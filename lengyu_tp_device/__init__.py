from dataclasses import dataclass

from mods_base import ENGINE, BoolOption, Mod, build_mod, get_pc, keybind
from unrealsdk import find_enum, logging, make_struct
from unrealsdk.unreal import UObject

from networking import add_network_functions, host
from ui_utils import show_hud_message

ENetMode = find_enum("ENetMode")

MOD_NAME: str = "Lengyu TP Device"
# Disable this mod in the Digistruct Peak map
_BLOCKED_MAP_NAME: str = "TestingZone_P"

mod: Mod | None = None


@dataclass
class LocationInfo:
    map_name: str
    x: float
    y: float
    z: float
    pitch: int
    roll: int
    yaw: int


_show_tips_option: BoolOption = BoolOption(
    identifier="Show Tips",
    value=True,
    description="When enabled, tips related to this mod are displayed.",
)
_print_console_cmd_option: BoolOption = BoolOption(
    identifier="Print Console Command",
    value=False,
    description="When enabled, marking the current location prints the teleport console command to python-sdk.log.",
)

_saved_locations: list[LocationInfo | None] = [None, None, None]
_index: int = 0


def _is_client() -> bool:
    """Whether this is a client in a multiplayer game (single player and host both return False)."""
    return ENGINE.GetCurrentWorldInfo().NetMode == ENetMode.NM_Client


def _is_blocked_by_game_state() -> bool:
    """Disable this mod while using a vehicle or while in the Digistruct Peak map"""
    pc = get_pc()
    if pc is None or pc.IsUsingVehicle(True):
        return True
    map_name = pc.WorldInfo.GetMapName()
    return map_name is None or map_name == _BLOCKED_MAP_NAME


def _show_feedback(message: str, duration: float = 2.0) -> None:
    """Replacement for the old DisplayFeedback: uses show_hud_message from the new SDK to show HUD info"""
    if not _show_tips_option.value:
        return
    show_hud_message(MOD_NAME, message, duration)


def _print_console_cmd(x: float, y: float, z: float) -> None:
    if not _print_console_cmd_option.value:
        return
    logging.info(f"set WillowPlayerPawn Location (x={int(x)},y={int(y)},z={int(z)})")


def _teleport(pc: UObject, x: float, y: float, z: float, pitch: int, roll: int, yaw: int) -> None:
    # The new SDK returns a copy when reading a struct property, so it must be assigned as a whole
    # instead of assigning each component like the old version did
    pc.Pawn.Location = make_struct("Vector", X=x, Y=y, Z=z)
    pc.Rotation = make_struct("Rotator", Pitch=pitch, Roll=roll, Yaw=yaw)


def _teleport_to_player(pc: UObject | None, other_pc: UObject | None) -> None:
    if pc is None or pc.Pawn is None or other_pc is None or other_pc.Pawn is None:
        return
    location = other_pc.Pawn.Location
    pc.Pawn.Location = make_struct("Vector", X=location.X + 100, Y=location.Y + 100, Z=location.Z)


# Multiplayer core: the client sends the teleport request to the host, which performs it
# (when the host calls it itself, it runs locally right away).
# While running, func.sender is the PlayerReplicationInfo of the requesting player, so passing
# a PlayerID around manually (as the old version did) is no longer needed.
@host.json_message
def _server_teleport(x: float, y: float, z: float, pitch: int, roll: int, yaw: int) -> None:
    pc = _server_teleport.sender.Owner
    if pc is None:
        return
    _teleport(pc, x, y, z, pitch, roll, yaw)


@host.json_message
def _server_teleport_to_player(player_pri_index: int) -> None:
    sender_pri = _server_teleport_to_player.sender
    pri_array = ENGINE.GetCurrentWorldInfo().GRI.PRIArray

    # Find player number player_pri_index among the players other than the requester
    other_pc: UObject | None = None
    i = 1
    for pri in pri_array:
        if pri == sender_pri:
            continue
        if i == player_pri_index:
            other_pc = pri.Owner
        i += 1
    _teleport_to_player(sender_pri.Owner, other_pc)


def _mark_location() -> None:
    if _index not in range(len(_saved_locations)):
        return
    pc = get_pc()
    location = pc.Pawn.Location
    rotation = pc.Rotation
    _saved_locations[_index] = LocationInfo(
        pc.WorldInfo.GetMapName(),
        location.X,
        location.Y,
        location.Z,
        rotation.Pitch,
        rotation.Roll,
        rotation.Yaw,
    )
    _print_console_cmd(location.X, location.Y, location.Z)
    _show_feedback(f'Saved the current location to slot <font color="#4DFFFF">{_index + 1}</font>.')


def _load_location() -> None:
    if _index not in range(len(_saved_locations)) or _saved_locations[_index] is None:
        return

    pc = get_pc()
    saved = _saved_locations[_index]

    # Check that the map matches
    if pc.WorldInfo.GetMapName() != saved.map_name:
        _show_feedback(
            f'Cannot teleport. The marker in slot <font color="#4DFFFF">{_index + 1}</font> is not in the current map.',
            5.0,
        )
        return

    # Teleport!
    if _is_client():
        _server_teleport(saved.x, saved.y, saved.z, saved.pitch, saved.roll, saved.yaw)
    else:
        _teleport(pc, saved.x, saved.y, saved.z, saved.pitch, saved.roll, saved.yaw)


def _select_slot(index: int) -> None:
    global _index
    _index = index


def _teleport_me_to_other_player(player_pri_index: int) -> None:
    if not 1 <= player_pri_index <= 3:
        return
    if _is_client():
        _server_teleport_to_player(player_pri_index)
        return

    pri_array = ENGINE.GetCurrentWorldInfo().GRI.PRIArray
    if player_pri_index < len(pri_array):
        _teleport_to_player(get_pc(), pri_array[player_pri_index].Owner)


@keybind("Mark Location", "NumPadZero")
def mark_location() -> None:
    if _is_blocked_by_game_state():
        return
    _mark_location()


@keybind("Teleport", "Decimal")
def load_location() -> None:
    if _is_blocked_by_game_state():
        return
    _load_location()


@keybind("Change to Slot 1", "NumPadOne")
def select_slot_1() -> None:
    if _is_blocked_by_game_state():
        return
    _select_slot(0)


@keybind("Change to Slot 2", "NumPadTwo")
def select_slot_2() -> None:
    if _is_blocked_by_game_state():
        return
    _select_slot(1)


@keybind("Change to Slot 3", "NumPadThree")
def select_slot_3() -> None:
    if _is_blocked_by_game_state():
        return
    _select_slot(2)


@keybind("Teleport You to Player 1", "NumPadFour")
def teleport_to_player_1() -> None:
    if _is_blocked_by_game_state():
        return
    _teleport_me_to_other_player(1)


@keybind("Teleport You to Player 2", "NumPadFive")
def teleport_to_player_2() -> None:
    if _is_blocked_by_game_state():
        return
    _teleport_me_to_other_player(2)


@keybind("Teleport You to Player 3", "NumPadSix")
def teleport_to_player_3() -> None:
    if _is_blocked_by_game_state():
        return
    _teleport_me_to_other_player(3)


mod = build_mod(
    keybinds=[
        mark_location,
        load_location,
        select_slot_1,
        select_slot_2,
        select_slot_3,
        teleport_to_player_1,
        teleport_to_player_2,
        teleport_to_player_3,
    ],
    options=[
        _show_tips_option,
        _print_console_cmd_option,
    ],
)
# Register the network functions so they are enabled/disabled together with the mod
add_network_functions(mod)
