import math

from mods_base import ENGINE, Game, Mod, build_mod, get_pc, keybind
from unrealsdk import find_enum, find_object, make_struct
from unrealsdk.unreal import UObject

from networking import add_network_functions, host

ENetMode = find_enum("ENetMode")

# Gap between two adjacent loots on the circle
INTERNAL_BETWEEN_LOOT: int = 36

mod: Mod | None = None


def _is_client() -> bool:
    """Whether this is a client in a multiplayer game (single player and host both return False)."""
    return ENGINE.GetCurrentWorldInfo().NetMode == ENetMode.NM_Client


def _get_valid_loots() -> list[UObject]:
    """Mission items, unpickupable items and ECHOs are not counted"""
    return [
        pickup
        for pickup in get_pc().GetWillowGlobals().PickupList
        if pickup is not None
        and not pickup.bIsMissionItem
        and pickup.Inventory.GetZippyFrame() not in ("None", "Moxxtail")
        and pickup.bPickupable
    ]


def _remove_loots(loots: list[UObject]) -> None:
    for loot in loots:
        loot.LifeSpan = 0.1


def _collect_loots(x: float, y: float, z: float) -> None:
    """Group the loots by rarity and arrange them in a circle around (x, y, z)"""
    valid_loots = _get_valid_loots()

    loots_by_rarity: dict[int, list[UObject]] = {}
    for loot in valid_loots:
        loots_by_rarity.setdefault(loot.InventoryRarityLevel, []).append(loot)

    n = len(valid_loots)
    radius = n * INTERNAL_BETWEEN_LOOT / (2 * math.pi)

    j = 0
    for loots in loots_by_rarity.values():
        for loot in loots:
            loot.Location = make_struct(
                "Vector",
                X=x + radius * math.cos(2 * math.pi / n * j),
                Y=y + radius * math.sin(2 * math.pi / n * j),
                Z=z,
            )
            loot.AdjustPickupPhysicsAndCollisionForBeingDropped()
            loot.InitializePickupForRBPhysics()
            j += 1


# Multiplayer core: the client sends the collect request to the host, which performs it
# (when the host calls it itself, it runs locally right away).
# While running, func.sender is the PlayerReplicationInfo of the requesting player, so passing
# a PlayerID around manually (as the old version did) is no longer needed.
@host.message
def _collect_loot_on_host() -> None:
    location = _collect_loot_on_host.sender.Owner.Pawn.Location
    _collect_loots(location.X, location.Y, location.Z)


@keybind("Collect Loot", "Slash")
def collect_loot() -> None:
    if _is_client():
        _collect_loot_on_host()
    else:
        location = get_pc().Pawn.Location
        _collect_loots(location.X, location.Y, location.Z)


@keybind("Delete Whites and Greens", "Subtract")
def delete_white_green_loot() -> None:
    if _is_client():
        # In a multiplayer game, non-host players can only use collect loot
        return

    rarity_colors = find_object("GlobalsDefinition", "GD_Globals.General.Globals").RarityLevelColors
    white_green_life_span_types = (
        rarity_colors[1].DropLifeSpanType,
        rarity_colors[2].DropLifeSpanType,
    )
    _remove_loots(
        [loot for loot in _get_valid_loots() if loot.LifeSpanType in white_green_life_span_types],
    )


@keybind("Delete All Loot", "Delete")
def delete_all_loot() -> None:
    if _is_client():
        return
    _remove_loots(_get_valid_loots())


mod = build_mod(
    keybinds=[
        collect_loot,
        delete_white_green_loot,
        delete_all_loot,
    ],
)
# Register the network functions so they are enabled/disabled together with the mod
add_network_functions(mod)
