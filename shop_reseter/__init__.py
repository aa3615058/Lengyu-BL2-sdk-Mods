from mods_base import Game, Mod, build_mod, get_pc, hook, keybind
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

# The legacy sdk split an object's ObjectFlags into two 32 bit halves (A and B), while the new sdk
# returns a single 64 bit int, so only the lower 32 bits used to be compared.
_SHOP_FLAGS: int = 0x4100000
_FLAGS_MASK: int = 0xFFFFFFFF

mod: Mod | None = None
_shop: UObject | None = None


@hook("WillowGame.VendingMachineExGFxMovie:extInitVendingMachine", Type.PRE)
def shop_reorder(
    this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    global _shop
    _shop = this.VM


@keybind("Reset Shop", "F9")
def reset_shop() -> None:
    if _shop is None:
        return

    if (_shop.ObjectFlags & _FLAGS_MASK) != _SHOP_FLAGS:
        return

    if Game.get_current() == Game.TPS:
        _shop.ResetInventory()
    else:
        get_pc().ServerPlayerResetShop(_shop)


mod = build_mod(
    hooks=[
        shop_reorder,
    ],
    keybinds=[
        reset_shop,
    ],
)
