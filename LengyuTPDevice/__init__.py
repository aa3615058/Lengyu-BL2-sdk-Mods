from typing import List
import unrealsdk
from ..ModMenu import EnabledSaveType, SDKMod, ModTypes, Keybind, OptionManager, Options, Game, RegisterMod, Hook

class LocationInfo:
    def __init__(self, MapName, X, Y, Z, Pitch, Roll, Yaw):
        self.MapName=MapName
        self.X=X
        self.Y=Y
        self.Z=Z
        self.Pitch=Pitch
        self.Roll=Roll
        self.Yaw=Yaw

class LengyuTPDevice(SDKMod):
    Name: str = "lengyuTPDevice"
    Version: str = "1.1"
    Author: str = "lengyu"
    Description: str = "Allows you to teleport yourself anywhere you marked. \n1.Press NUM0 to mark the location. \n2.Press NUMdot to teleport.\n3.Press NUM1-3 to switch within 3 slots.\n\nIt doesn't work in the map Digistruct Peak."
    Types: ModTypes = ModTypes.Utility
    SupportedGames = Game.BL2
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    def __init__(self):
        self.gameSpeed = unrealsdk.UObject.FindObjectsContaining("WillowCoopGameInfo WillowGame.Default__WillowCoopGameInfo")[0].GameSpeed
        self.Marks:List[LocationInfo] = [None, None, None]
        self.Index = 0
        self.Keybinds: List[Keybind] = [
            Keybind("mark location", "NumPadZero"),
            Keybind("teleport", "Decimal"),
            Keybind("change to the slot 1", "NumPadOne"),
            Keybind("change to the slot 2", "NumPadTwo"),
            Keybind("change to the slot 3", "NumPadThree"),
        ]
        
        self.showTips = True
        self.Options = [
            OptionManager.Options.Boolean(
                "Show Tips",
                "When it is enbale, you will see tips when you press the keybinds.",
                StartingValue=True
            )
        ]

    def ModOptionChanged(self, option: OptionManager.Options.Base, new_value) -> None:
        if option.Caption == "Show Tips":
            self.showTips = new_value

    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == "mark location":
            self.SaveLocation()
        elif name == "teleport":
            self.LoadLocation()
        elif name == "change to the slot 1":
            self.Index = 0
        elif name == "change to the slot 2":
            self.Index = 1
        elif name == "change to the slot 3":
            self.Index = 2
    
    def DisplayFeedback(self, message, time=2.0) -> None:
        if self.showTips:
            playerController = unrealsdk.GetEngine().GamePlayers[0].Actor
            HUDMovie = playerController.GetHUDMovie()
            if HUDMovie is None:
                return
            duration = time * self.gameSpeed
            HUDMovie.ClearTrainingText()
            HUDMovie.AddTrainingText(
                message, "TPDevice", duration, (), "", False, 0, playerController.PlayerReplicationInfo, True
            )

    def SaveLocation(self) -> None:
        if self.Index not in range(0,len(self.Marks)):
            return
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor
        if pc.WorldInfo.GetMapName() is None or pc.WorldInfo.GetMapName() == "TestingZone_P":
            return
        
        locale = pc.Pawn.Location
        rotate = pc.Rotation
        self.Marks[self.Index]=LocationInfo(pc.WorldInfo.GetMapName(),locale.x,locale.y,locale.z,rotate.Pitch,rotate.Roll,rotate.Yaw)
        self.DisplayFeedback("Current location is saved to the <font color=\"#4DFFFF\">slot {}</font>.".format(self.Index+1))

    def LoadLocation(self) -> None:
        if self.Index not in range(0,len(self.Marks)) or self.Marks[self.Index] is None:
            return
        
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor
        if pc.WorldInfo.GetMapName() is None or pc.WorldInfo.GetMapName() == "TestingZone_P":
            return
        
        if not pc.IsPrimaryPlayer():
            self.DisplayFeedback("You are not allowed to teleport in a game which is not created by yourself", 3.0)
            return
        
        if pc.WorldInfo.GetMapName() != self.Marks[self.Index].MapName:
            self.DisplayFeedback("Error! The saved location of the <font color=\"#4DFFFF\">slot {}</font> is not in current map.".format(self.Index+1), 5.0)
            return
        
        pc.Pawn.Location.X = self.Marks[self.Index].X
        pc.Pawn.Location.Y = self.Marks[self.Index].Y
        pc.Pawn.Location.Z = self.Marks[self.Index].Z
        pc.Rotation.Pitch = self.Marks[self.Index].Pitch
        pc.Rotation.Roll = self.Marks[self.Index].Roll
        pc.Rotation.Yaw = self.Marks[self.Index].Yaw

RegisterMod(LengyuTPDevice())
