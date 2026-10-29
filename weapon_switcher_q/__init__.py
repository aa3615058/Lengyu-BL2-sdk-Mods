from mods_base import Mod, build_mod, get_pc, hook, keybind
from unrealsdk.hooks import Type
from unrealsdk.unreal import UObject, WrappedStruct, BoundFunction

mod: Mod | None = None
_previous_weapon = None

def _is_normal_weapon(weapon) -> bool:
    try:
        return weapon.Class.Name == "WillowWeapon"
    except:
        return False
            
@hook("WillowGame.WillowPlayerController:NotifyChangedWeapon", Type.POST)
def weapon_listener(this:UObject, args:WrappedStruct, ret, func:BoundFunction) -> None:
    global _previous_weapon
    if args.PreviousWeapon is None or args.NewWeapon is None:
        return
    
    if not this.IsLocalPlayerController():
        return
    
    if _is_normal_weapon(args.NewWeapon) and _is_normal_weapon(args.PreviousWeapon):
        if args.NewWeapon != args.PreviousWeapon:
           _previous_weapon = args.PreviousWeapon
    return

@keybind("Last Used Weapon", "Q")
def switch_weapon() -> None:
    global _previous_weapon
    try:
        if _previous_weapon:
            pc = get_pc()
            if not pc.IsUsingVehicle(False):
                inv = pc.GetPawnInventoryManager()
                if _previous_weapon in inv.getEquippedWeapons(None, None, None, None):
                    inv.setCurrentWeapon(_previous_weapon, False)
    except:
        return

mod = build_mod(
    hooks=[
        weapon_listener
    ],
    keybinds=[
        switch_weapon
    ]
)
