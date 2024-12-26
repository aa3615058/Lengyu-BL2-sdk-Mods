from typing import List
from math import sin, cos, pi
import unrealsdk

from ..ModMenu import EnabledSaveType, KeybindManager, SDKMod, Game, ServerMethod


class LootCollector(SDKMod):
    Name: str = "Loot Collector"
    Version: str = "1.4"
    Author: str = "Lengyu"
    Description: str = "Help you collect loot conveniently. \n" \
                       "1.Press / to teleport all loot to you. These loot will form a circle around you and be sorted by rarity level. \n" \
                       "2.Press - (on keypad) to delete all white and green loot. \n" \
                       "3.Press Delete to delete all loot. (CAUTION)\n" \
                       "Mission items ,unpickupable items and ECHOs will be excluded.\n" \
                       "In multiplayer games, the client player cannot delete items."
    Types = unrealsdk.ModTypes.Utility
    SupportedGames = Game.BL2 | Game.TPS

    Keybinds: List[KeybindManager.Keybind] = [
        KeybindManager.Keybind("Collect Loots", Key="Slash"),
        KeybindManager.Keybind("Delete Whites and Greens", Key="Subtract"),
        KeybindManager.Keybind("Delete All Loots", Key="Delete")
        ]
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    def __init__(self) -> None:
        super().__init__()
        self.internalOfLoots = 36

    def GameInputPressed(self, bind: KeybindManager.Keybind, event: KeybindManager.InputEvent) -> None:
        if bind.Name == "Collect Loots":
            if self.AmIClientPlayer():
                self.ServerCollectLoots(self.GetMyClientPlayerID())
            else:
                PlayerLocation = self.GetPlayerController().Pawn.Location
                self.CollectLoots(PlayerLocation.X, PlayerLocation.Y, PlayerLocation.Z)
        if self.AmIClientPlayer():
            return
        if bind.Name == "Delete All Loots":
            ValidLoots = self.GetValidLoots()
            self.RemoveLoots(ValidLoots)
        if bind.Name == "Delete Whites and Greens":
            ValidLoots = self.GetValidLoots()
            RarityLevelColors = unrealsdk.FindObject("GlobalsDefinition", "GD_Globals.General.Globals").RarityLevelColors
            ValidLoots = [
                pickup for pickup in ValidLoots
                if pickup.LifeSpanType == RarityLevelColors[1].DropLifeSpanType or pickup.LifeSpanType == RarityLevelColors[2].DropLifeSpanType
            ]
            self.RemoveLoots(ValidLoots)

    def RemoveLoots(self, loots):
        for loot in loots:
            loot.LifeSpan = 0.1

    @ServerMethod
    def ServerCollectLoots(self, PlayerID: int):
        for PRI in unrealsdk.GetEngine().GetCurrentWorldInfo().GRI.PRIArray:
            if PRI.Owner.PlayerReplicationInfo.PlayerID == PlayerID:
                PlayerLocation = PRI.Owner.Pawn.Location
                self.CollectLoots(PlayerLocation.X, PlayerLocation.Y, PlayerLocation.Z)
                return
        return

    def CollectLoots(self, x: int, y: int, z: int):
        ValidLoots = self.GetValidLoots()
        LootByRarity = {}
        for LootA in ValidLoots:
            if LootA.InventoryRarityLevel not in LootByRarity:
                LootByRarity[LootA.InventoryRarityLevel] = []
            LootByRarity[LootA.InventoryRarityLevel].append(LootA)

        m = self.internalOfLoots
        n = len(ValidLoots)
        p = n*m/(2*pi)
        
        j = 0
        for rarity, Loot in enumerate(LootByRarity.values()):              
            for LootA in Loot:
                LootA.Location = (x+p*cos(2*pi/n*j), y+p*sin(2*pi/n*j), z)
                LootA.AdjustPickupPhysicsAndCollisionForBeingDropped()
                LootA.InitializePickupForRBPhysics()
                j += 1

    def GetPlayerController(self):
        return unrealsdk.GetEngine().GamePlayers[0].Actor

    def GetMyClientPlayerID(self):
        return self.GetPlayerController().PlayerReplicationInfo.PlayerID

    def AmIClientPlayer(self) -> bool:
        return unrealsdk.GetEngine().GetCurrentWorldInfo().NetMode == 3

    def GetValidLoots(self) -> List[unrealsdk.UObject]:
        return [
            pickup for pickup in self.GetPlayerController().GetWillowGlobals().PickupList
            if not (pickup.bIsMissionItem == True or pickup.Inventory.GetZippyFrame() == "None" or pickup.bPickupable == False)
        ]

unrealsdk.RegisterMod(LootCollector())
