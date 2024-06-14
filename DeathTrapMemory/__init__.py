import unrealsdk
import json
import os
from typing import List
from ..ModMenu import EnabledSaveType, SDKMod, Hook, Game, ModTypes, Keybind

        
class DeathTrapMemory(SDKMod):
    Name = "Death Trap Memory Program"
    Version = "1.1"
    Author = "Lengyu"
    Description = "Memory program for Death Trap. You can press the keybind(default: 6) to save the data of your equipped shield. Death Trap will always copy the shield you saved if it is in your backpack.\nThe Memory is persistent.\nTo erase the memory, you could remove your shield and press the keybind again."
    ModTypes = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.LoadWithSettings
    SupportedGames = Game.BL2

    def __init__(self):
        self.DTShield_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "DTMemory.json")
        self.ShieldID = 0
        self.ShieldName = ""
        self.ShowTips = True
        self.IsMechromancer = False

        self.Keybinds: List[Keybind] = [
            Keybind("Memorize shield data", "Six"),
        ]
    
    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == "Memorize shield data":
            pc = unrealsdk.GetEngine().GamePlayers[0].Actor
            charClass = pc.CharacterClass
            if charClass is None or str.find(charClass.Name,"Mechromancer") < 0:
                self.IsMechromancer = False
            else:
                self.IsMechromancer = True

            if self.IsMechromancer:
                Pawn = pc.Pawn
                Shield = Pawn.EquippedItems[0]
                if Shield:
                    if Shield.GetUniqueID():
                        self.ShieldID = Shield.GetUniqueID()
                        self.ShieldName = str.split(Shield.GenerateHumanReadableName()," ")[-1].strip()
                        self.DisplayFeedback(f"Death Trap has memorized the data of <font color=\"#4DFFFF\">{self.ShieldName}</font>.",time=4.0)
                else:
                    self.ShieldID = 0
                    self.ShieldName = ""
                    self.DisplayFeedback("Death Trap has erased the memory.",time=4.0)

    @Hook("WillowGame.DeathtrapActionSkill.TryToShareShields","MemorizeShield")
    def MemorizeShield(self, 
                    caller: unrealsdk.UObject, 
                    function: unrealsdk.UFunction, 
                    params: unrealsdk.FStruct):
        playerController: unrealsdk.UObject = params.TheController
        playerPawn: unrealsdk.UObject = params.TheWillowPawn
        deathTrap: unrealsdk.UObject = caller.DeathTrap

        if playerController is None or playerPawn is None or deathTrap is None:
            return True
        
        backpackInventory = playerPawn.InvManager.Backpack
        if backpackInventory is None:
            return True
        
        if playerPawn.EquippedItems[0].getUniqueID() == self.ShieldID:
            return True
        
        Shield = None
        if self.ShieldID:
            for item in backpackInventory:
                if item.GetUniqueID() == self.ShieldID:
                    Shield = item
                    break

        if Shield:
            Shield = item.CreateClone()
            Shield.bDropOnDeath = False
            Shield.GiveTo(deathTrap, True)
            return False
        else:
            return True
    
    @Hook("WillowGame.WillowSaveGameManager.SaveGame","SaveDTShield")
    def SaveDTShield(self,
                    caller: unrealsdk.UObject,
                    function: unrealsdk.UFunction,
                    params: unrealsdk.FStruct
        ) -> bool:
        if params.Filename is None or not params.Filename.endswith(".sav"):
            return True
        
        if not self.IsMechromancer:
            return True
        
        try:
            data={}
            with open(self.DTShield_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            
            data[params.Filename] = {
                "ShieldID": self.ShieldID,
                "ShieldName": self.ShieldName,
            }
            with open(self.DTShield_path, "w", encoding="utf-8") as f:
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
            with open(self.DTShield_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if params.Filename in data:
                    shieldID = data[params.Filename]["ShieldID"]
                    if shieldID:
                        self.ShieldID = shieldID
                    shieldName = data[params.Filename]["ShieldName"]
                    if shieldName:
                        self.ShieldName = shieldName
                    self.IsMechromancer = True
                else:
                    self.ShieldID = 0
                    self.ShieldName = ""
                    self.IsMechromancer = False
        except:
            self.ShieldID = 0
            self.ShieldName = ""
            self.IsMechromancer = False
        finally:
            return True
    
    def DisplayFeedback(self, message, time=2.0) -> None:
        if self.ShowTips:
            playerController = unrealsdk.GetEngine().GamePlayers[0].Actor
            HUDMovie = playerController.GetHUDMovie()
            if HUDMovie is None:
                return
            duration = time
            HUDMovie.ClearTrainingText()
            HUDMovie.AddTrainingText(
                message, "Death Trap Memory Program", duration, (), "", False, 0, playerController.PlayerReplicationInfo, True
            )
    

unrealsdk.RegisterMod(DeathTrapMemory())