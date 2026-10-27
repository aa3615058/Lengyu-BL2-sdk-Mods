from mods_base import Mod, build_mod, get_pc, hook
from unrealsdk.hooks import Type
from unrealsdk.unreal import UObject, WrappedStruct, BoundFunction
from unrealsdk import logging

mod: Mod | None = None

@hook("WillowGame.FrontendGFxMovie:OnTick", Type.POST)
def fix_Chinese_trans(this:UObject, args:WrappedStruct, ret, func:BoundFunction) -> None:
    try:
        pc = get_pc()
        pc.ConsoleCommand(fr"set GD_Weap_SniperRifles.Name.Title_Vladof.Title_Legendary_Lyudmila PartName 鲁达")
        pc.ConsoleCommand(fr"set GD_AttributePresentation.Skills_Siren.AttrPresent_Mindseye Description 灵犀之眼")
    finally:
        #remove_hook("WillowGame.FrontendGFxMovie.OnTick", Type.POST, "fix_Chinese_trans")
        fix_Chinese_trans.disable()

mod = build_mod(
    hooks=[
        fix_Chinese_trans
    ]
)
