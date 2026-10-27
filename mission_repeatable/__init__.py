from mods_base import BoolOption, Mod, build_mod, get_pc, hook
from unrealsdk import find_object, logging
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

# (mission location and giver, possible side effects, mission object path, default switch state)
_MISSIONS: dict[str, tuple[str, str, str, bool]] = {
    "Fibber": ("Eridium Blight, Mal - A Real Boy: Human", "", "GD_Z2_ARealBoy.M_ARealBoy_Human", True),
    "Pimpernel": ("Washburne Refinery, C3n50r807 - Don't Copy That Floppy","",
    "GD_Orchid_SM_FloppyCopy.m_orchid_dontcopythatfloppy",True),
    "Swordsplosion": ("Flamerock Refuge, Roland - The Sword in The Stoner", "", "GD_Aster_SwordInStone.m_swordinstoner", True),
    "Kitten": ("Badass Crater Bar, Moxxi - Everybody Wants to be Wanted", "", "GD_IrisHUB_Wanted.m_irishub_wanted", True),
    "Heartbreaker": ("Sanctuary, Marcus - Safe and Sound","",        "GD_Z2_SafeAndSound.M_SafeAndSound",True),
    "Rubi": ("Sanctuary, Mordecai - Rakkaholics Anonymous", "", "GD_Z2_Rakkaholics.M_Rakkaholics", True),
    "Lady Fist": ("The Dust, Bounty Board - Uncle Teddy", "", "GD_Z3_UncleTeddy.M_UncleTeddy", True),
    "Amigo Sincero": ("The Backburner, Brick - BFFFs","",        "GD_Anemone_Side_EyeSnipers.m_anemone_eyeofthesnipers",True),
    "Hail": ("Fink's Slaughterhouse, Fink - Bandit Slaughter: Round 5","",     "GD_Z1_BanditSlaughter.M_BanditSlaughter5",True),
    "Creamer": ("Natural Selection Annex, Captain Cabrera - Creature Slaughter: Round 5","",
    "GD_Z2_CreatureSlaughter.M_CreatureSlaughter_5",True),
    "Chere-amie": ("Innuendobot 5000 - Hyperion Slaughter: Round 5","",
    "GD_Z3_RobotSlaughter.M_RobotSlaughter_5",True),
    "Orc": ("Murderlin's Temple, Murderlin the Wizard - Magic Slaughter: Round 5","",
    "GD_Aster_TempleSlaughter.m_templeslaughter5",True),
    "Love Thumper": (
        "Gift box dropped by stalkers - Best Mother's Day Ever",
        # This mission is not accepted from a fixed NPC: any stalker death has a 25% chance to drop
        # a gift box (Behavior_SpawnItems in GD_StalkerShared.Death.DeathDef_Stalker, the pool is
        # IP_TaggartMomGift), and only picking the gift box up accepts the mission. Just setting the
        # mission to repeatable is not enough, see the comment of _mother_gift_box_reusable below.
        "After the mission is completed the gift box can be dropped again.",
        "GD_Z2_MothersDayGift.BalanceDefs.M_MothersDayGift",
        True,
    ),
    "Sand Hawk": (
        "Washburne Refinery, C3n50r807 - I Know It When I See It",
        "The mission reward is changed to the Sand Hawk, the mission becomes repeatable, and Don't Copy That Floppy no longer requires this mission to be completed first.",
        "GD_Orchid_SM_KnowIt.m_orchid_knowitwhenseeit",
        True,
    ),
    "Evolve Varkid": ("Natural Selection Annex, Captain Cabrera - Creature Slaughter: Round 2","",
    "GD_Z2_CreatureSlaughter.M_CreatureSlaughter_2",True),
    "Treasure of the Sands": ("Oasis, Bounty Board - Treasure of the Sands","",
    "GD_Orchid_SideMissions.Missions.Mission_TreasureOfTheSands",True),
}

_MAL_IDENTIFIER: str = "Fibber"
_SAND_HAWK_IDENTIFIER: str = "Sand Hawk"
_PIMPERNEL_IDENTIFIER: str = "Pimpernel"
_MOTHER_IDENTIFIER: str = "Love Thumper"

_SAND_HAWK_BALANCE: str = "GD_Orchid_BossWeapons.SMG.SMG_Dahl_3_SandHawk"

# Specific to Love Thumper (Best Mother's Day Ever):
# the mission itself is GD_Z2_MothersDayGift.BalanceDefs.M_MothersDayGift,
# the gift box that starts it is GD_Z2_MothersDayGiftData.ItemDefs.ID_TaggartMomGift
# (a MissionItemDefinition: MissionDirective=the mission above, AssociatedMissionObjective=None,
#  meaning it is a "mission giver item" rather than a "mission objective item").
_MOTHER_MISSION: str = _MISSIONS[_MOTHER_IDENTIFIER][2]
_MOTHER_GIFT_ITEM: str = "GD_Z2_MothersDayGiftData.ItemDefs.ID_TaggartMomGift"

# IMission.EMissionStatus: 0=not accepted 1=in progress 2=all objectives done 3=ready to turn in 4=completed 5=failed
_STATUS_DONE_OR_FAILED: tuple[int, ...] = (4, 5)

_mother_enabled: bool = True
_mother_object: UObject | None = None

mod: Mod | None = None


def _find_object(cls: str, name: str) -> UObject | None:
    """The old FindObject returned None when nothing was found, the new one raises ValueError, so wrap it."""
    try:
        return find_object(cls, name)
    except ValueError:
        return None


def _set_mission_repeatable(mission_path: str, repeatable: bool) -> None:
    mission = _find_object("MissionDefinition", mission_path)
    if mission is not None:
        mission.bRepeatable = repeatable


def _deal_mission_hawk(enable: bool) -> None:
    """Extra handling for the Sand Hawk mission"""
    mission_hawk = _find_object("MissionDefinition", _MISSIONS[_SAND_HAWK_IDENTIFIER][2])
    mission_pimpernel = _find_object("MissionDefinition", _MISSIONS[_PIMPERNEL_IDENTIFIER][2])

    if enable:
        sand_hawk = _find_object("WeaponBalanceDefinition", _SAND_HAWK_BALANCE)
        # Set the reward item of I Know It When I See It to the Sand Hawk
        if mission_hawk is not None and sand_hawk is not None:
            mission_hawk.Reward.RewardItems = [sand_hawk]
        # Make Don't Copy That Floppy require no prerequisite I Know It When I See It
        if mission_pimpernel is not None:
            mission_pimpernel.Dependencies[0] = None
    else:
        # Set the reward item of I Know It When I See It to none (same as vanilla)
        if mission_hawk is not None:
            mission_hawk.Reward.RewardItems = []
        # Make Don't Copy That Floppy require the prerequisite I Know It When I See It (same as vanilla)
        if mission_pimpernel is not None and mission_hawk is not None:
            mission_pimpernel.Dependencies[0] = mission_hawk


# Make sure Mal always respawns
@hook("Engine.Behavior_RemoteEvent:ApplyBehaviorToContext", Type.PRE)
def _prevent_mal_unspawnable(
    this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    return Block if this.EventName == "ARealBoy_TurnOffMalSpawner" else None


# Make sure Mal is always interactable
@hook("WillowGame.WillowAIPawn:Behavior_ChangeUsability", Type.PRE)
def _prevent_mal_unusable(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    if (
        args.ChangeType == 2
        and this.AIClass._path_name() == "GD_PinocchioBot.Character.CharClass_PinocchioBot"
        and this.HasAnyMissionsForPlayer()
    ):
        return Block
    return None


def _set_mal_hooks(enabled: bool) -> None:
    if enabled:
        _prevent_mal_unspawnable.enable()
        _prevent_mal_unusable.enable()
    else:
        _prevent_mal_unspawnable.disable()
        _prevent_mal_unusable.disable()


def _set_mother_enabled(enabled: bool) -> None:
    global _mother_enabled
    _mother_enabled = enabled


def _mission_status(mission: UObject) -> int:
    """The real status of this mission in the player's mission list.

    MissionTracker.GetMissionStatus is not called - that function is blocked by the hook below,
    calling it here would bite its own tail. Reading the save data in MissionPlaythroughs is enough.
    """
    pc = get_pc()
    if pc is None:
        return -1
    try:
        for playthrough in pc.MissionPlaythroughs:
            for entry in playthrough.MissionList:
                if entry.MissionDef == mission:
                    return int(entry.Status)
    except Exception:  # noqa: BLE001
        return -1
    return -1


def _mother_mission() -> UObject | None:
    global _mother_object
    if _mother_object is None:
        _mother_object = _find_object("MissionDefinition", _MOTHER_MISSION)
    return _mother_object


@hook("WillowGame.MissionTracker:GetMissionStatus", Type.PRE)
def _mother_gift_box_reusable(
    _this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    """Make the engine read a completed/failed Love Thumper mission as "not accepted".

    This mission is not given by an NPC, it is started by a gift box (ID_TaggartMomGift) dropped by
    stalkers, and the engine's checks for a "mission giver item" all live in WillowPickup, three of
    them hard-require the mission status to be == not accepted (0):
      - WillowPickup.InitializeFromInventory
      - WillowPickup.SetPickupStatusFromMissionTracker   -> decides bPickupable (whether it can be picked up)
      - WillowPickup.RegisterMissionDirector             -> decides whether it is registered as a "mission giver"
    A repeatable mission however stays at "completed (4)" after being turned in - WillowPlayerController.AddMission
    and UpdateMissionStatus keep dedicated status==4 && bRepeatable branches, which shows the status never
    goes back to 0. So the gift box still drops (WillowMissionItem.MissionDenyPickup only blocks when
    "status is not 0 and the prerequisite is not met" or "there already is one on the ground"), yet it
    cannot be picked up and does not give the mission again - which is exactly the pitfall of only setting
    bRepeatable. Here we only lie for this single mission, and only while it is completed/failed; while the
    mission is in progress (1/2/3) the real status is returned as usual.
    """
    if not _mother_enabled:
        return None
    mission = _mother_mission()
    if mission is None or args.InMission != mission or not mission.bRepeatable:
        return None
    if _mission_status(mission) not in _STATUS_DONE_OR_FAILED:
        return None
    return Block


def _mother_entry() -> tuple[object, int] | None:
    """The Love Thumper entry in the player's mission list (tuple: entry, index), None if not found."""
    pc = get_pc()
    mission = _mother_mission()
    if pc is None or mission is None:
        return None
    try:
        idx = pc.NativeGetMissionIndex(mission)
        if idx < 0:
            return None
        playthrough = pc.GetCurrentPlaythrough()
        return (pc.MissionPlaythroughs[playthrough].MissionList[idx], idx)
    except Exception:  # noqa: BLE001
        return None


@hook("WillowGame.WillowPlayerController:AddMission", Type.POST)
def _mother_fix_accepted_status(
    _this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    """Correct the status written into the player's mission list when "re-accepting" to in progress (1).

    Inside AddMission it is `MStatus.Status = GetMissionStatus(InMission)` (WillowPlayerController.uc:3188/3214),
    and to make the gift box pickable we lie to the engine that the completed 4 is 0 - so what is written on
    re-accept is **0**. All three following stages of UpdateMissionStatus have prerequisites though: going to
    "all objectives done (2)" requires the old status to be 1, going to "ready to turn in (3)" requires the old
    status to be 1 or 2, and going to "completed (4)" requires the old status to be 2 or 3. With an old status
    of 0 everything is skipped:
      - turning in takes the else branch -> "No reward, you already got a reward in a previous mission"
        (NoRewardExplanation_Complete);
      - there is no "ready to turn in (3)" status -> the green question mark at the turn in point never shows up.
    The only thing fixed here is: after accepting, write the status as 1, then 1->2->3->4 works normally and the
    reward and the question mark both come back.
    """
    if not _mother_enabled:
        return
    mission = _mother_mission()
    if mission is None or args.InMission != mission:
        return
    found = _mother_entry()
    if found is None:
        return
    entry, _idx = found
    try:
        if int(entry.Status) != 1:
            entry.Status = 1
    except Exception:  # noqa: BLE001
        pass


def _mother_try_marker(pickup: UObject) -> None:
    """The first dropped gift box has a yellow exclamation mark because WillowPickup.RegisterMissionDirector
    attaches MissionDirectorSocket/MissionDirectorParticle; that function likewise hard-requires the mission
    status to be == not accepted (0). Once the gift box is pickable and has settled on the ground, register it
    one more time here."""
    if not _mother_enabled:
        return
    try:
        if not pickup.bIsMissionDirector or not pickup.bPickupable or not pickup.bPickupAtRest:
            return
        if pickup.MissionDirectorParticle is not None:
            return
        inventory = pickup.Inventory
        if inventory is None:
            return
        item_def = inventory.GetInventoryDefinition()
        if item_def is None or item_def._path_name() != _MOTHER_GIFT_ITEM:
            return
        pickup.RegisterMissionDirector()
    except Exception:  # noqa: BLE001
        pass


@hook("WillowGame.WillowPickup:SetPickupability", Type.POST)
def _mother_marker_on_pickable(
    this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    _mother_try_marker(this)


@hook("WillowGame.WillowPickup:ReplicatedEvent", Type.POST)
def _mother_marker_on_rest(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    if str(args.VarName) == "bPickupAtRest":
        _mother_try_marker(this)


def _on_mission_option_changed(option: BoolOption, new_value: bool) -> None:
    _set_mission_repeatable(_MISSIONS[option.identifier][2], new_value)
    if option.identifier == _MAL_IDENTIFIER:
        _set_mal_hooks(new_value)
    elif option.identifier == _SAND_HAWK_IDENTIFIER:
        _deal_mission_hawk(new_value)
    elif option.identifier == _MOTHER_IDENTIFIER:
        _set_mother_enabled(new_value)


_mission_options: list[BoolOption] = [
    BoolOption(
        identifier=key,
        value=data[3],
        description=f"{data[0]}. This mission becomes repeatable. {data[1]}",
        on_change_while_enabled=_on_mission_option_changed,
    )
    for key, data in _MISSIONS.items()
]


# Apply every enabled mission setting once after the game has loaded.
# This cannot be omitted: the SDK loads mods far too early, at which point find_object may not find the
# mission objects yet and some changes do not take effect, so wait for the first OnTick and disable this
# hook afterwards.
@hook("WillowGame.FrontendGFxMovie:OnTick", Type.PRE)
def _apply_missions_on_first_tick(
    _this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    try:
        for option in _mission_options:
            if not option.value:
                continue
            _set_mission_repeatable(_MISSIONS[option.identifier][2], True)
            if option.identifier == _SAND_HAWK_IDENTIFIER:
                _deal_mission_hawk(True)
    except Exception as ex:  # noqa: BLE001
        logging.error(str(ex))
    finally:
        _apply_missions_on_first_tick.disable()


def on_enable() -> None:
    for option in _mission_options:
        if option.identifier == _MAL_IDENTIFIER and option.value:
            _set_mal_hooks(True)
        elif option.identifier == _MOTHER_IDENTIFIER:
            _set_mother_enabled(option.value)


def on_disable() -> None:
    _set_mal_hooks(False)
    _set_mother_enabled(False)


mod = build_mod(
    hooks=[
        _apply_missions_on_first_tick,
        _mother_gift_box_reusable,
        _mother_fix_accepted_status,
        _mother_marker_on_pickable,
        _mother_marker_on_rest,
    ],
    options=_mission_options,
)
