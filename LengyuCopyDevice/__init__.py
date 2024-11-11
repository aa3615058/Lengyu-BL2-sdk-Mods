import unrealsdk
from ..ModMenu import EnabledSaveType, SDKMod, ModTypes, Game, KeybindManager, RegisterMod, Hook, ServerMethod

class LengyuCopyDevice(SDKMod):
    Name: str = "Lengyu Copy Device"
    Version: str = "1.0"
    Author: str = "Lengyu"
    Description: str = "Allows you to spend money to copy the selected equipment.\nPress the keybind \"UseSecondary\" on the Equipment page or Backpack page to throw and copy the selected equipment. It costs the selling price of the equipment.\nIt works in multiplayer game when both the server player and the client player have enabled this mod."
    Types: ModTypes = ModTypes.Utility
    SupportedGames = Game.BL2 | Game.TPS
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings
    InputNames = []
    OptionNames = []
    ToolTipName = "copy"
    DefaultWillowInventory = None

    def __init__(self):
        self.DefaultWillowInventory = unrealsdk.ConstructObject(Class="WillowShield",Name="DefaultWillowShield")
        unrealsdk.KeepAlive(self.DefaultWillowInventory)
    
    @Hook("WillowGame.StatusMenuInventoryPanelGFxObject.SetTooltipText")
    def CopyDeviceToolTip(
        self,
        caller: unrealsdk.UObject,
        function: unrealsdk.UFunction,
        params: unrealsdk.FStruct,
    ) -> bool:
        pc = caller.ParentMovie.WPCOwner
        key = pc.PlayerInput.GetKeyForAction("UseSecondary", True)
        
        sep = "\n"
        if caller.bInEquippedView is True:         
           sep = "  "
        text = f"{params.TooltipsText}{sep}[{key}] {self.ToolTipName}"
        caller.SetTooltipText(text)
        return False
    
    @Hook("WillowGame.StatusMenuInventoryPanelGFxObject.NormalInputKey")
    def CopyDeviceInputKey(
        self,
        caller: unrealsdk.UObject,
        function: unrealsdk.UFunction,
        params: unrealsdk.FStruct,
    ) -> bool:
        if params.uevent != KeybindManager.InputEvent.Pressed:
            return True

        if caller.bInitialSetupFinished is False:
            return True

        if caller.SwitchToQueuedInputHandler(params.ukey, params.uevent):
            return True

        pc = caller.ParentMovie.WPCOwner
        pawn = pc.Pawn
        if pc is None or pawn is None:
            return True
        
        if (params.ukey == pc.PlayerInput.GetKeyForAction("UseSecondary", True) and pc.PlayerInput.bUsingGamepad == False) or (params.ukey == 'XboxTypeS_Y' and pc.PlayerInput.bUsingGamepad == True):
            if caller.bInEquippedView is False:
                caller.BackpackPanel.SaveState()

            item = caller.GetSelectedThing()
            if caller.CanDrop(item) is False:
                return False
            
            price = item.GetMonetaryValue()
            repInfo = pc.PlayerReplicationInfo
            if price > repInfo.GetCurrencyOnHand(0):
                return False

            itemA = item.CreateClone()
            caller.DropSelectedThing()
            caller.ParentMovie.SetTooltipsText()
            if self.AmIClientPlayer():
                self.ServerGiveItem(itemA.GetSerialNumberString(), repInfo.PlayerID)
            else:
                self.GiveItem(pawn, itemA)

            repInfo.AddCurrencyOnHand(0, -price)

            if caller.bInEquippedView is False:
                caller.BackpackPanel.RestoreState()
            
            return False
        return True

    @ServerMethod
    def ServerGiveItem(self, ItemID: str, PlayerID: int):
        for PRI in unrealsdk.GetEngine().GetCurrentWorldInfo().GRI.PRIArray:
            if PRI.Owner.PlayerReplicationInfo.PlayerID == PlayerID:
                pawn = PRI.Owner.Pawn
                item = self.DefaultWillowInventory.CreateInventoryFromSerialNumberString(ItemID, pawn)[0]
                self.GiveItem(pawn, item)
                return

    def GiveItem(self, Pawn:unrealsdk.UObject, Item:unrealsdk.UObject):
        Item.GiveTo(Pawn, False)
    
    def AmIClientPlayer(self) -> bool:
        return unrealsdk.GetEngine().GetCurrentWorldInfo().NetMode == 3

RegisterMod(LengyuCopyDevice())
