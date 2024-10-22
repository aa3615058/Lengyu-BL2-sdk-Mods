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
    Name: str = "lengyu TP Device"
    Version: str = "1.2"
    Author: str = "Lengyu"
    Description: str = "Allows you to teleport yourself anywhere you marked. \n1.Press NUM0 to mark the location. \n2.Press NUMDot to teleport.\n3.Press NUM1-3 to switch within 3 slots.\n4.Press NUM4-6 to teleport other player to you.\n5.Open the option to print teleport console command when you mark location.\nIn co-op game it only works for the host player.\nIt doesn't work in the map Digistruct Peak."
    Types: ModTypes = ModTypes.Utility
    SupportedGames = Game.BL2 | Game.TPS
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings
    InputNames = ["mark location", "teleport", "change to slot 1", "change to slot 2", "change to slot 3", "teleport player2 to host player", "teleport player3 to host player", "teleport player4 to host player"]
    OptionNames = ["Show Tips", "Print Console Command"]

    def __init__(self):
        self.SavedLocaiton:List[LocationInfo] = [None, None, None]
        self.Index = 0
        self.Keybinds: List[Keybind] = [
            Keybind(self.InputNames[0], "NumPadZero"),
            Keybind(self.InputNames[1], "Decimal"),
            Keybind(self.InputNames[2], "NumPadOne"),
            Keybind(self.InputNames[3], "NumPadTwo"),
            Keybind(self.InputNames[4], "NumPadThree"),
            Keybind(self.InputNames[5], "NumPadFour"),
            Keybind(self.InputNames[6], "NumPadFive"),
            Keybind(self.InputNames[7], "NumPadSix"),            
        ]
        
        self.ShowTipsOption = OptionManager.Options.Boolean(self.OptionNames[0], "When it is enable, you will see tips when you press the keybinds.", True)
        self.PrintConsoleCmdOption = OptionManager.Options.Boolean(self.OptionNames[1], "When it is enable, teleport console command will be printed in python-sdk.log when you mark location.", False)

        self.Options = [
            self.ShowTipsOption,
            self.PrintConsoleCmdOption,            
        ]
        
    def ModOptionChanged(self, option: OptionManager.Options.Base, new_value) -> None:
        if option.Caption == self.OptionNames[0]:
            pass
        elif option.Caption == self.OptionNames[1]:
            pass

    def GameInputPressed(self, input) -> None:
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor
        name = input.Name

        if pc is None or pc.IsUsingVehicle(True):
            return
            
        if pc.WorldInfo.GetMapName() is None or pc.WorldInfo.GetMapName() == "TestingZone_P":
            return

        if name == self.InputNames[5]:
            self.TeleportOtherPlayer(2)
        elif name == self.InputNames[6]:
            self.TeleportOtherPlayer(3)
        elif name == self.InputNames[7]:
            self.TeleportOtherPlayer(4)
        
        if name == self.InputNames[0]:
            self.SaveLocation()
        elif name == self.InputNames[1]:
            self.LoadLocation()
        elif name == self.InputNames[2]:
            self.Index = 0
        elif name == self.InputNames[3]:
            self.Index = 1
        elif name == self.InputNames[4]:
            self.Index = 2

    def Enable(self) -> None:
        super().Enable()

    def Disable(self) -> None:
        super().Disable()
    
    def DisplayFeedback(self, message, time=2.0) -> None:
        if self.ShowTipsOption.CurrentValue:
            playerController = unrealsdk.GetEngine().GamePlayers[0].Actor
            HUDMovie = playerController.GetHUDMovie()
            if HUDMovie is None:
                return
            duration = time
            HUDMovie.ClearTrainingText()
            HUDMovie.AddTrainingText(
                message, "TP Device", duration, (), "", False, 0, playerController.PlayerReplicationInfo, True
            )

    def SaveLocation(self) -> None:
        if self.Index not in range(0,len(self.SavedLocaiton)):
            return
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor        
        locale = pc.Pawn.Location
        rotate = pc.Rotation
        self.SavedLocaiton[self.Index]=LocationInfo(pc.WorldInfo.GetMapName(),locale.x,locale.y,locale.z,rotate.Pitch,rotate.Roll,rotate.Yaw)
        self.PrintConsoleCmd(locale.x, locale.y, locale.z)
        self.DisplayFeedback("Current location is saved to <font color=\"#4DFFFF\">slot {}</font>.".format(self.Index+1))

    def LoadLocation(self) -> None:
        if self.Index not in range(0,len(self.SavedLocaiton)) or self.SavedLocaiton[self.Index] is None:
            return
        
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor

        if self.AmIClientPlayer():
            self.DisplayFeedback("You are not allowed to teleport in a game which is not created by yourself", 3.0)
            return
        
        if pc.WorldInfo.GetMapName() != self.SavedLocaiton[self.Index].MapName:
            self.DisplayFeedback("Error! The saved location of <font color=\"#4DFFFF\">slot {}</font> is not in current map.".format(self.Index+1), 5.0)
            return
        
        # TP!
        pc.Pawn.Location.X = self.SavedLocaiton[self.Index].X
        pc.Pawn.Location.Y = self.SavedLocaiton[self.Index].Y
        pc.Pawn.Location.Z = self.SavedLocaiton[self.Index].Z
        pc.Rotation.Pitch = self.SavedLocaiton[self.Index].Pitch
        pc.Rotation.Roll = self.SavedLocaiton[self.Index].Roll
        pc.Rotation.Yaw = self.SavedLocaiton[self.Index].Yaw
        
    def PrintConsoleCmd(self, x, y, z):
        if self.PrintConsoleCmdOption.CurrentValue:
            Cmd = f"set WillowPlayerPawn Location (x={int(x)},y={int(y)},z={int(z)})"
            unrealsdk.Log(f"{self.Name}: {Cmd}")
    
    def TeleportOtherPlayer(self, playerIndex: int):
        if playerIndex < 2 or playerIndex > 4:
            return
        if self.AmIClientPlayer():
            return
        
        PRIArray = unrealsdk.GetEngine().GetCurrentWorldInfo().GRI.PRIArray
        playerIndex = playerIndex - 1
        if playerIndex < len(PRIArray):
            Otherpc = PRIArray[playerIndex].Owner
            pc = unrealsdk.GetEngine().GamePlayers[0].Actor
            # TP!
            Otherpc.Pawn.Location.X = pc.Pawn.Location.X + 100
            Otherpc.Pawn.Location.Y = pc.Pawn.Location.Y + 100
            Otherpc.Pawn.Location.Z = pc.Pawn.Location.Z
    
    def AmIClientPlayer(self) -> bool:
        return unrealsdk.GetEngine().GetCurrentWorldInfo().NetMode == 3

RegisterMod(LengyuTPDevice())
