from mods_base import Mod, build_mod, get_pc, hook, keybind
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

_weapon_id: int = 0

@hook("WillowGame.WillowPickup:InitializePickupForRBPhysics", Type.PRE)
def _pickup_our_weapon_back(
    this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    global _weapon_id

    if _weapon_id == 0:
        return

    inventory = this.Inventory
    if inventory is None or inventory.GetUniqueID() != _weapon_id:
        return

    _weapon_id = 0
    get_pc().PickupPickupable(this, False)


@keybind("Throw Weapon Then Pickup It", "H")
def throw_weapon_then_pickup() -> None:
    global _weapon_id

    pc = get_pc()
    if pc.IsUsingVehicle(False) or pc.Pawn is None:
        return

    weapon = pc.Pawn.Weapon
    if weapon is None:
        return

    _weapon_id = weapon.GetUniqueID()
    try:
        _pickup_our_weapon_back.enable()
        pc.ThrowWeapon()
    finally:
        _pickup_our_weapon_back.disable()
        _weapon_id = 0


mod: Mod = build_mod(
    hooks=[],
    keybinds=[throw_weapon_then_pickup],
)