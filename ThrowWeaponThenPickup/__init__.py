import unrealsdk
from typing import List
from ..ModMenu import EnabledSaveType, SDKMod, Game, ModTypes, Keybind

class ThrowWeaponThenPickup(SDKMod):
    Name = "Throw Weapon Then Pickup"
    Version = "1.0"
    Author = "Lengyu"
    Description = "Adds a keybind option to the game that allows you to throw the current weapon and then pick up it immediately. \nThe benefit of doing this is: \n1.Switch weapon immediately. 2.Reloading magazine immediately.\n By default the key is binded to H."
    ModTypes = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.LoadWithSettings
    SupportedGames = Game.BL2 | Game.TPS

    def __init__(self):
        self.Flag = False
        self.WeaponID = 0
        self.Keybinds: List[Keybind] = [
            Keybind("Throw current weapon then pickup it", "H"),
        ]

    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == "Throw current weapon then pickup it":
            pc = unrealsdk.GetEngine().GamePlayers[0].Actor
            if not pc.IsUsingVehicle(False):
                self.WeaponID = pc.Pawn.Weapon.GetUniqueID()
                unrealsdk.RegisterHook("WillowGame.WillowPickup.InitializePickupForRBPhysics", "PickupBackWeapon", ThrowWeaponThenPickup.PickupOurWeaponBack)
                pc.ThrowWeapon()
                unrealsdk.RemoveHook("WillowGame.WillowPickup.InitializePickupForRBPhysics", "PickupBackWeapon")
                self.WeaponID = 0
                pass

    def PickupOurWeaponBack(
            caller: unrealsdk.UObject,
            function: unrealsdk.UFunction,
            params: unrealsdk.FStruct
    ) -> bool:
        #unrealsdk.Log("WeaponID: " + str(self.WeaponID))
        #unrealsdk.Log("Pickupable ID: " + str(caller.Inventory.GetUniqueID()))
        try:
            if __self__.WeaponID != 0 and __self__.WeaponID == caller.Inventory.GetUniqueID():
                __self__.WeaponID = 0
                pc = unrealsdk.GetEngine().GamePlayers[0].Actor
                pc.PickupPickupable(caller, False)
        finally:
            return True

__self__ = ThrowWeaponThenPickup()
unrealsdk.RegisterMod(__self__)