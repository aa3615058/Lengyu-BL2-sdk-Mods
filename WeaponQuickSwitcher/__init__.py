import unrealsdk
from typing import List
from ..ModMenu import EnabledSaveType, SDKMod, Hook, Game, ModTypes, Keybind

class WeaponQuickSwitcher(SDKMod):
    Name = "Weapon Quick Switcher"
    Version = "1.1"
    Author = "Lengyu"
    Description = "Adds a keybind option to the game that allows you to switch to the last used weapon like in Counter-Strike and many other FPS games. By default the key is binded to Q."
    ModTypes = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.LoadWithSettings
    SupportedGames = Game.BL2 | Game.TPS

    def __init__(self):
        self.PreviousWeapon = None

        self.Keybinds: List[Keybind] = [
            Keybind("Last Used Weapon", "Q"),
        ]

    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == "Last Used Weapon":
            if self.PreviousWeapon:
                pc = unrealsdk.GetEngine().GamePlayers[0].Actor
                if not pc.IsUsingVehicle(False):
                    inv_manager = pc.GetPawnInventoryManager()
                    if self.HasWeaponEquiped(self.PreviousWeapon, inv_manager):
                        inv_manager.setCurrentWeapon(self.PreviousWeapon, False)

    @Hook("WillowGame.WillowPlayerController.NotifyChangedWeapon","SwitchWeaponListener")
    def weaponListener(self,
            caller: unrealsdk.UObject,
            function: unrealsdk.UFunction,
            params: unrealsdk.FStruct
    ) -> bool:
        if params.PreviousWeapon is None or params.NewWeapon is None:
            return True
        
        if self.isNormalWeapon(params.NewWeapon) and self.isNormalWeapon(params.PreviousWeapon):
            if params.NewWeapon != params.PreviousWeapon:
                self.PreviousWeapon = params.PreviousWeapon
        return True
    
    def isNormalWeapon(self, weapon) -> bool:
        try:
            return weapon.Class == unrealsdk.FindClass("WillowWeapon")
        except:
            return False

    def HasWeaponEquiped(self, weapon, inv_manager) -> bool:
        try:
            return weapon in inv_manager.getEquippedWeapons()
        except:
            return False

unrealsdk.RegisterMod(WeaponQuickSwitcher())