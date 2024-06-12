import unrealsdk
from ..ModMenu import EnabledSaveType, SDKMod, Hook, Game, ModTypes

class SimpleChineseFix(SDKMod):
    Name = "Simple Chinese Fix"
    Version = "1.0"
    Author = "lengyu"
    Description = "Fix several inexplicably invalid Simple Chinese Language localization words.\nLyuda = 鲁达\nMinds Eye Skill = 灵犀之眼"
    ModTypes = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.LoadWithSettings
    SupportedGames = Game.BL2

    def __init__(self):
        super(SimpleChineseFix, self).__init__()

    def Enable(self):
        super().Enable()

    def Disable(self):
        super().Disable()
    
    @Hook("WillowGame.FrontendGFxMovie.OnTick","fixTrans1")
    def FixChineseTrans(self,
            caller: unrealsdk.UObject,
            function: unrealsdk.UFunction,
            params: unrealsdk.FStruct
    ) -> bool:
        try:
            pc=unrealsdk.GetEngine().GamePlayers[0].Actor
            pc.ConsoleCommand(fr"set GD_Weap_SniperRifles.Name.Title_Vladof.Title_Legendary_Lyudmila PartName 鲁达")
            pc.ConsoleCommand(fr"set GD_AttributePresentation.Skills_Siren.AttrPresent_Mindseye Description 灵犀之眼")
        finally:
            unrealsdk.RemoveHook("WillowGame.FrontendGFxMovie.OnTick", "fixTrans1")
            return True

unrealsdk.RegisterMod(SimpleChineseFix())