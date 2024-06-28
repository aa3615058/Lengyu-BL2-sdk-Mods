from typing import List
from math import sin, cos, pi
import unrealsdk

from ..ModMenu import EnabledSaveType, KeybindManager, SDKMod, Game


class LootCollector(SDKMod):
    Name: str = "Loot Collector"
    Version: str = "1.3"
    Author: str = "Lengyu"
    Description: str = "Help you collect loot conveniently. \n" \
                       "1.Press / to teleport all loot to you. These loot will form a circle around you and be sorted by rarity level. \n" \
                       "2.Press - (on keypad) to delete all white and green loot. \n" \
                       "3.Press Delete to delete all loot. (CAUTION)\n" \
                       "Mission items ,unpickupable items and ECHOs will be excluded.\n" \
                       "In multiplayer games, it will work only when you are the host player."
    Types = unrealsdk.ModTypes.Utility
    SupportedGames = Game.BL2

    Keybinds: List[KeybindManager.Keybind] = [
        KeybindManager.Keybind("Collect Loot", Key="Slash"),
        KeybindManager.Keybind("Delete Whites and Greens", Key="Subtract"),
        KeybindManager.Keybind("Delete All Loot", Key="Delete")
        ]
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    def __init__(self) -> None:
        super().__init__()
        self.internalBetweenLoot=36

    def GameInputPressed(self, keybind: KeybindManager.Keybind, event: KeybindManager.InputEvent) -> None:
        if event != KeybindManager.InputEvent.Released:
            return
        if keybind.Name == "Collect Loot":
            if self.AmIClientPlayer():
                return
            
            ValidLoot = self.GetValidLoot()

            SortedLoot = {}
            for Loot in ValidLoot:
                if Loot.InventoryRarityLevel not in SortedLoot:
                    SortedLoot[Loot.InventoryRarityLevel] = []
                SortedLoot[Loot.InventoryRarityLevel].append(Loot)

            playerLocation = self.GetPC().Pawn.Location
            px, py, pz = playerLocation.X, playerLocation.Y, playerLocation.Z
            
            m = self.internalBetweenLoot
            n = len(ValidLoot)
            p = n*m/(2*pi)
            
            j = 0
            for rarity, Loot in enumerate(SortedLoot.values()):              
                for LootA in Loot:
                    LootA.Location = (px+p*cos(2*pi/n*j), py+p*sin(2*pi/n*j), pz)
                    LootA.AdjustPickupPhysicsAndCollisionForBeingDropped()
                    LootA.InitializePickupForRBPhysics()
                    j += 1

        if keybind.Name == "Delete All Loot":
            if self.AmIClientPlayer():
                return
            ValidLoot = self.GetValidLoot()
            self.RemoveLoot(ValidLoot)
        if keybind.Name == "Delete Whites and Greens":
            if self.AmIClientPlayer():
                return
            ValidLoot = self.GetValidLoot()
            RarityLevelColors = unrealsdk.FindObject("GlobalsDefinition", "GD_Globals.General.Globals").RarityLevelColors
            ValidLoot = [
                pickup for pickup in ValidLoot
                if pickup.LifeSpanType == RarityLevelColors[1].DropLifeSpanType or pickup.LifeSpanType == RarityLevelColors[2].DropLifeSpanType
            ]
            self.RemoveLoot(ValidLoot)

    def RemoveLoot(self, Loot):
        for LootA in Loot:
            LootA.LifeSpan = 0.1

    def GetPC(self):
        return unrealsdk.GetEngine().GamePlayers[0].Actor
    
    def AmIClientPlayer(self) -> bool:
        return unrealsdk.GetEngine().GetCurrentWorldInfo().NetMode == 3
    
    def GetValidLoot(self) -> List[unrealsdk.UObject]:
        return [
            pickup for pickup in self.GetPC().GetWillowGlobals().PickupList
            if not (pickup.bIsMissionItem == True or pickup.Inventory.GetZippyFrame() == "None" or pickup.bPickupable == False)
        ]

unrealsdk.RegisterMod(LootCollector())
