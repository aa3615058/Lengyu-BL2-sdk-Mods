import unrealsdk
import json
import os
from typing import List
from ..ModMenu import EnabledSaveType, SDKMod, OptionManager, Game, ModTypes, Keybind, Hook, ServerMethod, ClientMethod
 
class DeathTrapMemory(SDKMod):
    Name = "Death Trap Memory Program"
    Version = "1.4"
    Author = "Lengyu"
    Description = "Memory program for Death Trap. You can press the keybind(default: 6) to save the data of your equipped shield. Death Trap will always copy the shield you saved if it is in your backpack.\nThe Memory is persistent.\nTo erase the memory, you could remove your shield and press the keybind again.\nIt works in multiplayer game when both the server player and the client player have enabled this mod."
    ModTypes = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.LoadWithSettings
    SupportedGames = Game.BL2
    InputNames = ["Memorize shield data"]
    OptionNames = ["Show Info"]

    def __init__(self):
        self.FileName = "DTMemory.json"
        self.DTShiledNameSuffix = "★DT"
        
        self.FilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.FileName)
        self.ShieldID  = ""
        self.ShieldName = ""
        self.AmIMechromancer = False
        self.DefaultWillowShield = None
        
        self.ShowTipsOption = OptionManager.Options.Boolean(self.OptionNames[0], "When it is enable, you will see information about the DeathTrap's shield.", True)

        self.Keybinds: List[Keybind] = [
            Keybind(self.InputNames[0], "Six"),
        ]

        self.Options = [
            self.ShowTipsOption,         
        ]
    
    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == self.InputNames[0]:
            pc = self.GetPC()
            charClass = pc.CharacterClass
            if charClass is None or str.find(charClass.Name, "Mechromancer") < 0:
                self.AmIMechromancer = False
            else:
                self.AmIMechromancer = True

            if self.AmIMechromancer:
                playerShield = pc.Pawn.EquippedItems[0]
                if playerShield:
                    self.ShieldID = playerShield.GetSerialNumberString()
                    self.ShieldName = self.GenerateDTShieldName(playerShield)
                    self.DisplayFeedback(f"Death Trap has memorized the data of <font color=\"#4DFFFF\">{self.ShieldName}</font>.",time=4.0)
                else:
                    self.ShieldID = ""
                    self.ShieldName = ""
                    self.DisplayFeedback("Death Trap has erased his memory.")
            pass

    def ModOptionChanged(self, option: OptionManager.Options.Base, new_value) -> None:
        if option.Caption == self.OptionNames[0]:
            pass

    @ServerMethod
    def ServerGiveDeathTrapShield(self, ShieldID : str, PlayerID : int):
        for PRI in unrealsdk.GetEngine().GetCurrentWorldInfo().GRI.PRIArray:
            if PRI.Owner.PlayerReplicationInfo.PlayerID == PlayerID:
                Pawn = PRI.Owner.Pawn
                DeathTrap = Pawn.MyActionSkill.DeathTrap

                self.GiveDeathTrapShield(Pawn, DeathTrap, ShieldID)
                
                DTShield = DeathTrap.EquippedItems[0]
                if DTShield:
                    DTShieldName = self.GenerateDTShieldName(DTShield)
                    self.ClientDisPlayDeathTrapShield(DTShieldName, PlayerID)
                return

    def GiveDeathTrapShield(self,
                            Pawn:unrealsdk.UObject,
                            DeathTrap:unrealsdk.UObject,
                            ShieldID:str):

        if Pawn is None or DeathTrap is None or ShieldID is None:
            return
        
        pc = Pawn.GetController()
        if pc is None:
            return

        shareShieldsSkill = Pawn.MyActionSkill.ShareShieldsSkill
        if shareShieldsSkill is None:
            return

        skillManager = unrealsdk.GetEngine().GetCurrentWorldInfo().Game.GetSkillManager()
        if skillManager is None or not skillManager.IsSkillActive(pc, shareShieldsSkill):
            return
        
        DTShield = None
        if len(ShieldID) > 0:
            if self.DefaultWillowShield == None:
                self.DefaultWillowShield = unrealsdk.ConstructObject(Class="WillowShield",Name="DefaultWillowShield")
                unrealsdk.KeepAlive(self.DefaultWillowShield)
            DTShield = self.DefaultWillowShield.CreateInventoryFromSerialNumberString(ShieldID, Pawn)[0]
        else:
            PlayerShield = Pawn.EquippedItems[0]
            if PlayerShield is None:
                return
            DTShield = PlayerShield.CreateClone()

        DTShield.bDropOnDeath = False
        DTShield.GiveTo(DeathTrap, True)
        DeathTrap.FullyReplenishShields()
        
        if pc.IsLocalPlayerController():
            DTShieldName = self.GenerateDTShieldName(DTShield)
            self.DisPlayDeathTrapShield(DTShieldName)

    @ClientMethod
    def ClientDisPlayDeathTrapShield(self, ShieldName : str, PlayerID : int):
        pc = self.GetPC()
        if pc.PlayerReplicationInfo.PlayerID == PlayerID:
            self.DisPlayDeathTrapShield(ShieldName)
    
    def DisPlayDeathTrapShield(self, ShieldName : str):
        self.DisplayFeedback(f"Death Trap has copied <font color=\"#4DFFFF\">{ShieldName}</font> as its shield.")
    
    def GenerateDTShieldName(self, DTShield: unrealsdk.UObject) -> str:
        return str.split(DTShield.GenerateHumanReadableName()," ")[-1].strip()

    @Hook("WillowGame.DeathtrapActionSkill.TryToShareShields","CopyMemorizedShield")
    def CopyMemorizedShield(self, 
                    caller: unrealsdk.UObject, 
                    function: unrealsdk.UFunction, 
                    params: unrealsdk.FStruct):
        pawn = params.TheWillowPawn
        deathTrap = caller.DeathTrap
        shieldID = self.ShieldID
        pc = pawn.GetController()

        if pc is None:
            return False

        if not pc.IsLocalPlayerController():
            return True
        
        if not self.CheckShieldInBackpack(shieldID, pc.GetPawnInventoryManager().Backpack):
            shieldID = ""

        if self.AmIClientPlayer():
            self.ServerGiveDeathTrapShield(shieldID, pc.PlayerReplicationInfo.PlayerID)
            return False

        self.GiveDeathTrapShield(pawn, deathTrap, shieldID)
        return False

    def CheckShieldInBackpack(self, ShieldID: str, Backpack: unrealsdk.UObject) -> bool:
        if Backpack is None or ShieldID is None or len(ShieldID) == 0:
            return False

        for item in Backpack:
            if item.GetSerialNumberString() == ShieldID:
                return True

        return False

    @Hook("WillowGame.WillowSaveGameManager.SaveGame","SaveDTShield")
    def SaveDTShield(self,
                    caller: unrealsdk.UObject,
                    function: unrealsdk.UFunction,
                    params: unrealsdk.FStruct
        ) -> bool:
        if params.Filename is None or not params.Filename.endswith(".sav"):
            return True
        
        if not self.AmIMechromancer:
            return True
        
        try:
            data={}
            with open(self.FilePath, "r", encoding="utf-8") as file:
                data = json.load(file)
            
            data[params.Filename] = {
                "ShieldID": self.ShieldID,
                "ShieldName": self.ShieldName,
            }
            with open(self.FilePath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        finally:
            return True
    
    @Hook("WillowGame.WillowSaveGameManager.BeginLoadGame","LoadDTShield")
    def LoadDTShield(self,
                    caller: unrealsdk.UObject,
                    function: unrealsdk.UFunction,
                    params: unrealsdk.FStruct
        ) -> bool:
        if params.Filename is None or not params.Filename.endswith(".sav"):
            return True
        try:
            with open(self.FilePath, "r", encoding="utf-8") as file:
                data = json.load(file)
                if params.Filename in data:
                    shieldID = data[params.Filename]["ShieldID"]
                    if shieldID:
                        self.ShieldID = shieldID
                    shieldName = data[params.Filename]["ShieldName"]
                    if shieldName:
                        self.ShieldName = shieldName
                    self.AmIMechromancer = True
                else:
                    self.ShieldID = ""
                    self.ShieldName = ""
                    self.AmIMechromancer = False
        except:
            self.ShieldID = ""
            self.ShieldName = ""
            self.AmIMechromancer = False
        finally:
            return True
    
    @Hook("WillowGame.ItemCardGFxObject.SetItemCardEx","DTShieldModifyItemCard")
    def ModifyItemCard(self, 
                       caller: unrealsdk.UObject,
                       function: unrealsdk.UFunction,
                       params: unrealsdk.FStruct) -> bool:
        if not self.AmIMechromancer:
            return True
        item = params.InventoryItem.ObjectPointer
        if item is None or not item.GetSerialNumberString() == self.ShieldID:
            return True

        # Block SetTitle Once
        def BlockSetTitleOnce(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
            unrealsdk.RemoveHook("WillowGame.ItemCardGFxObject.SetTitle", "DeathTrapMemoryBlockSetTitleOnce")
            return False

        unrealsdk.RegisterHook("WillowGame.ItemCardGFxObject.SetTitle", "DeathTrapMemoryBlockSetTitleOnce", BlockSetTitleOnce)
        
        # It's very very strange that GlobalsDefinition.GetRarityColorForLevel() returns a random result ?!
        # Therefore, I use GlobalsDefinition.GetRarityLevelColorsIndexforLevel[] to get the color tuple.
        pc = self.GetPC()
        globals = pc.GetWillowGlobals().GetGlobalsDefinition()
        rarityColor = globals.RarityLevelColors[globals.GetRarityLevelColorsIndexforLevel(item.GetRarityLevel())].Color
        colorTuple = rarityColor.B,rarityColor.G,rarityColor.R,rarityColor.A
        
        caller.SetTitle(
            item.GetManufacturer().FlashLabelName,
            item.GetShortHumanReadableName() + self.DTShiledNameSuffix,
            colorTuple,
            item.GetZippyFrame(),
            item.GetElementalFrame(),
            item.IsReadied(),
        )

        return True
    
    def AmIClientPlayer(self) -> bool:
        return unrealsdk.GetEngine().GetCurrentWorldInfo().NetMode == 3
    
    def GetPC(self) -> unrealsdk.UObject:
        return unrealsdk.GetEngine().GamePlayers[0].Actor

    def DisplayFeedback(self, message, time=2.0) -> None:
        if self.ShowTipsOption.CurrentValue:
            pc = self.GetPC()
            HUDMovie = pc.GetHUDMovie()
            if HUDMovie is None:
                return
            HUDMovie.ClearTrainingText()
            HUDMovie.AddTrainingText(message, self.Name, time, (), "", False, 0, pc.PlayerReplicationInfo, True)

unrealsdk.RegisterMod(DeathTrapMemory())