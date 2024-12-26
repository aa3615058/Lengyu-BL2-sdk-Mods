import unrealsdk
from typing import List
from ..ModMenu import EnabledSaveType, SDKMod, Hook, Game, ModTypes, Keybind
        
class ShopReseter(SDKMod):
    Name = "Shop Reseter"
    Version = "1.1"
    Author = "Lengyu"
    Description = "Adds a keybind option to the game that allows you to reset any shop you last used immediately. Please leave the shop before you press the keybind. By default the key is binded to F9. \nIn multiplayer games, it will work when you are a client player."
    ModTypes = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.LoadWithSettings
    SupportedGames = Game.BL2 | Game.TPS

    def __init__(self):
        self.Shop = None

        self.Keybinds: List[Keybind] = [
            Keybind("reset shop", "F9"),
        ]

    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == "reset shop":
            if self.Shop and self.Shop.ObjectFlags.A == 0x4100000:
                if Game.GetCurrent() == Game.BL2:
                    pc = unrealsdk.GetEngine().GamePlayers[0].Actor
                    pc.ServerPlayerResetShop(self.Shop)
                elif Game.GetCurrent() == Game.TPS:
                    self.Shop.ResetInventory()

    @Hook("WillowGame.VendingMachineExGFxMovie.extInitVendingMachine","shopReorder")
    def shopReorder(self, 
                    caller: unrealsdk.UObject, 
                    function: unrealsdk.UFunction, 
                    params: unrealsdk.FStruct):
        self.Shop = caller.VM
        return True

unrealsdk.RegisterMod(ShopReseter())