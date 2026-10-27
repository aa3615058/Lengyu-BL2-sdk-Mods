import json
from typing import Any

from mods_base import (
    ENGINE,
    SETTINGS_DIR,
    BoolOption,
    Mod,
    ObjectFlags,
    build_mod,
    get_pc,
    hook,
    keybind,
)
from unrealsdk import construct_object, find_enum, find_object, make_struct
from unrealsdk.hooks import (
    Block,
    Type,
    add_hook,
    prevent_hooking_direct_calls,
    remove_hook,
)
from unrealsdk.unreal import (
    BoundFunction,
    UObject,
    WrappedArray,
    WrappedStruct,
)

from networking import add_network_functions, host, targeted
from ui_utils import show_hud_message

ENetMode = find_enum("ENetMode")

MOD_NAME: str = "Death Trap Memory"
# Appended to the item card title, used to mark the shield Death Trap will use
DT_SHIELD_NAME_SUFFIX: str = "★DT"
# Memory data file (the old version kept DTMemory.json in the mod dir, now it lives in the settings dir)
SAVE_DATA_FILE = SETTINGS_DIR / "death_trap_memory_save_data.json"
# Identifier of the one-shot hook that blocks SetTitle
_BLOCK_SET_TITLE_HOOK_ID: str = "DeathTrapMemoryBlockSetTitleOnce"

mod: Mod | None = None

_show_tips_option: BoolOption = BoolOption(
    identifier="Show Info",
    value=True,
    description="When enabled, shows information related to this mod.",
)

# Memorized shield data, persisted per save game in SAVE_DATA_FILE
_shield_id: str = ""
_shield_name: str = ""
_am_i_mechromancer: bool = False

# WillowShield.CreateInventoryFromSerialNumberString is a native static function, so it needs a
# WillowShield object to be called on: either the CDO (Default__WillowShield) or a blank template
# object works. It must only be fetched on first use - the game imports mods far too early, at
# which point the CDO may not exist yet and constructing an object is not safe either.
_template_shield: UObject | None = None


def _get_template_shield() -> UObject:
    """Get the object used to call static functions, looked up/constructed on first use"""
    global _template_shield
    if _template_shield is not None:
        return _template_shield

    try:
        # Prefer the class default object
        _template_shield = find_object("WillowShield", "Default__WillowShield")
    except ValueError:
        _template_shield = None

    if _template_shield is None:
        # Fallback: construct a blank template object under ENGINE (equivalent to the old
        # ConstructObject + KeepAlive). Note that Outer must not be None, otherwise the object is
        # invalid and any native function touching it crashes with an access violation.
        template = construct_object("WillowShield", ENGINE, "DefaultWillowShield", 1)
        # Outer is ENGINE (never collected), so adding KEEP_ALIVE to the template itself keeps it
        # from being garbage collected
        template.ObjectFlags |= ObjectFlags.KEEP_ALIVE
        _template_shield = template

    return _template_shield


def _is_client() -> bool:
    """Whether this is a client in a multiplayer game (single player and host both return False)."""
    return ENGINE.GetCurrentWorldInfo().NetMode == ENetMode.NM_Client


def _update_mechromancer_state(pc: UObject) -> bool:
    """Update and return whether the current character is a Mechromancer"""
    global _am_i_mechromancer
    char_class = pc.CharacterClass
    _am_i_mechromancer = char_class is not None and "Mechromancer" in char_class.Name
    return _am_i_mechromancer


def _show_feedback(message: str, duration: float = 2.0) -> None:
    """Replacement for the old DisplayFeedback: uses show_hud_message from the new SDK to show HUD info"""
    if not _show_tips_option.value:
        return
    show_hud_message(MOD_NAME, message, duration)


def _generate_dt_shield_name(dt_shield: UObject) -> str:
    return dt_shield.GenerateHumanReadableName().split(" ")[-1].strip()


def _check_shield_in_backpack(
    shield_id: str | None,
    backpack: WrappedArray[UObject] | None,
) -> bool:
    if backpack is None or shield_id is None or len(shield_id) == 0:
        return False

    for item in backpack:
        if item.GetSerialNumberString() == shield_id:
            return True

    return False


def _give_death_trap_shield(
    pawn: UObject | None,
    death_trap: UObject | None,
    shield_id: str | None,
) -> None:
    """Copy the memorized shield (or the currently equipped shield) to Death Trap"""
    if pawn is None or death_trap is None or shield_id is None:
        return

    pc = pawn.GetController()
    if pc is None:
        return

    share_shields_skill = pawn.MyActionSkill.ShareShieldsSkill
    if share_shields_skill is None:
        return

    skill_manager = ENGINE.GetCurrentWorldInfo().Game.GetSkillManager()
    if skill_manager is None or not skill_manager.IsSkillActive(pc, share_shields_skill):
        return

    dt_shield: UObject | None
    if len(shield_id) > 0:
        # The function signature has a const out string parameter (read-only reference), so the SDK
        # wraps the return value into a tuple: (new item, echoed serial number string). So, just
        # like the old version, take [0].
        dt_shield = _get_template_shield().CreateInventoryFromSerialNumberString(shield_id, pawn)[0]
    else:
        equipped = pawn.EquippedItems
        player_shield = equipped[0] if len(equipped) > 0 else None
        if player_shield is None:
            return
        dt_shield = player_shield.CreateClone()
    if dt_shield is None:
        return

    dt_shield.bDropOnDeath = False
    dt_shield.GiveTo(death_trap, True)
    death_trap.FullyReplenishShields()

    # Only local players see the tip; in multiplayer the client's shield is handled by the host,
    # and the result is sent back to the client through a network message for display
    if pc.IsLocalPlayerController():
        _show_feedback(
            f'Death Trap is now using <font color="#4DFFFF">{_generate_dt_shield_name(dt_shield)}</font> as its shield.',
        )


# Multiplayer core: the client sends the "give Death Trap a shield" request to the host, which
# performs it. While running, func.sender is the PlayerReplicationInfo of the requesting player,
# so passing a PlayerID around manually (as the old version did) is no longer needed.
@host.json_message
def _server_give_death_trap_shield(shield_id: str) -> None:
    pri = _server_give_death_trap_shield.sender
    pc = pri.Owner
    if pc is None or pc.Pawn is None:
        return

    pawn = pc.Pawn
    death_trap = pawn.MyActionSkill.DeathTrap
    _give_death_trap_shield(pawn, death_trap, shield_id)

    # The host side does not show a tip for the client (pc is not the local player controller),
    # so send the name of the shield Death Trap actually equipped back to the requesting client
    equipped = death_trap.EquippedItems
    dt_shield = equipped[0] if len(equipped) > 0 else None
    if dt_shield:
        _client_display_death_trap_shield(pri, _generate_dt_shield_name(dt_shield))


# Multiplayer core: the host sends the shield display message back to a specific client.
# The old version broadcast a ClientMethod to every player and filtered by PlayerID, the new
# version delivers it straight to the target player.
@targeted.json_message
def _client_display_death_trap_shield(shield_name: str) -> None:
    _show_feedback(
        f'Death Trap is now using <font color="#4DFFFF">{shield_name}</font> as its shield.',
    )


@keybind("Memorize Shield Data", "Six")
def _memorize_shield_data() -> None:
    global _shield_id, _shield_name

    pc = get_pc(possibly_loading=True)
    if pc is None:
        return

    # Refresh the flag whether this is a Mechromancer or not (the save hooks rely on it)
    if not _update_mechromancer_state(pc):
        return

    equipped = pc.Pawn.EquippedItems
    player_shield = equipped[0] if len(equipped) > 0 else None
    if player_shield:
        _shield_id = player_shield.GetSerialNumberString()
        _shield_name = _generate_dt_shield_name(player_shield)
        _show_feedback(
            f'Death Trap has memorized the full data of <font color="#4DFFFF">{_shield_name}</font>.',
            4.0,
        )
    else:
        _shield_id = ""
        _shield_name = ""
        _show_feedback("Death Trap's memory has been cleared.")


@hook("WillowGame.DeathtrapActionSkill:TryToShareShields", Type.PRE)
def _copy_memorized_shield(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    pawn = args.TheWillowPawn
    death_trap = this.DeathTrap
    shield_id = _shield_id
    pc = pawn.GetController()

    if pc is None:
        return Block

    # Multiplayer-host handling a client: run the original logic, the real result is handled by the
    # _server_give_death_trap_shield network message.
    # The function is not interrupted to accommodate the case where the host has this mod but the
    # client does not.
    if not pc.IsLocalPlayerController():
        return None

    # Check whether the shield is in the backpack
    # A multiplayer host does not have the client's backpack data, so the client's backpack must be
    # checked here
    # Multiplayer-client handling multiplayer-client (itself): check the backpack
    # Multiplayer-host handling multiplayer-host: check the backpack
    # Single player: check the backpack
    if not _check_shield_in_backpack(shield_id, pc.GetPawnInventoryManager().Backpack):
        # No such shield in the backpack, blank the shieldID and run the original logic
        shield_id = ""

    # Multiplayer-client handling multiplayer-client: call the host network message
    if _is_client():
        _server_give_death_trap_shield(shield_id)
        return Block

    # Multiplayer-host handling multiplayer-host, or single player
    _give_death_trap_shield(pawn, death_trap, shield_id)
    return Block


@hook("WillowGame.WillowSaveGameManager:SaveGame", Type.PRE)
def _save_dt_shield(
    _this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    filename = args.Filename
    if filename is None or not filename.endswith(".sav"):
        return

    if not _am_i_mechromancer:
        return

    try:
        data: dict[str, Any] = {}
        if SAVE_DATA_FILE.exists():
            with SAVE_DATA_FILE.open(encoding="utf-8") as file:
                data = json.load(file)

        data[filename] = {
            "ShieldID": _shield_id,
            "ShieldName": _shield_name,
        }
        with SAVE_DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception:  # noqa: BLE001
        # Same as the old version, silently ignore save failures
        pass


@hook("WillowGame.WillowSaveGameManager:BeginLoadGame", Type.PRE)
def _load_dt_shield(
    _this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    global _shield_id, _shield_name, _am_i_mechromancer

    filename = args.Filename
    if filename is None or not filename.endswith(".sav"):
        return

    try:
        with SAVE_DATA_FILE.open(encoding="utf-8") as file:
            data = json.load(file)
            if filename in data:
                shield_id = data[filename]["ShieldID"]
                if shield_id:
                    _shield_id = shield_id
                shield_name = data[filename]["ShieldName"]
                if shield_name:
                    _shield_name = shield_name
                _am_i_mechromancer = True
            else:
                _shield_id = ""
                _shield_name = ""
                _am_i_mechromancer = False
    except Exception:  # noqa: BLE001
        _shield_id = ""
        _shield_name = ""
        _am_i_mechromancer = False


def _block_set_title_once(
    _this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block]:
    # One-shot block of the SetTitle call the game makes inside SetItemCardEx, removed right after use
    _ = remove_hook("WillowGame.ItemCardGFxObject:SetTitle", Type.PRE, _BLOCK_SET_TITLE_HOOK_ID)
    return Block


@hook("WillowGame.ItemCardGFxObject:SetItemCardEx", Type.PRE)
def _modify_item_card(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> None:
    if not _am_i_mechromancer:
        return

    # New SDK object properties return the item object itself (the old version needed .ObjectPointer)
    item = args.InventoryItem

    # Can check whether this is a shield first
    if item is None or item.GetSerialNumberString() != _shield_id:
        return

    # FunStats (the part below the panel stats) conflicts with the equipment parts display mod, so unused

    # Register a one-shot hook that blocks the following SetTitle call inside SetItemCardEx
    _ = add_hook(
        "WillowGame.ItemCardGFxObject:SetTitle",
        Type.PRE,
        _BLOCK_SET_TITLE_HOOK_ID,
        _block_set_title_once,
    )

    # Very odd: GlobalsDefinition.GetRarityColorForLevel() returns a random result here,
    # so use GlobalsDefinition.GetRarityLevelColorsIndexforLevel[] to get the color
    pc = get_pc()
    globals_definition = pc.GetWillowGlobals().GetGlobalsDefinition()
    rarity_color = globals_definition.RarityLevelColors[
        globals_definition.GetRarityLevelColorsIndexforLevel(item.GetRarityLevel())
    ].Color
    # The color parameter of SetTitle is a byte Color struct (declared order is B,G,R,A),
    # the old code's tuple (B,G,R,A) happened to match the declared order one to one, this is the
    # equivalent explicit form
    rarity_color_struct = make_struct(
        "Color",
        B=rarity_color.B,
        G=rarity_color.G,
        R=rarity_color.R,
        A=rarity_color.A,
    )

    # Python direct calls also trigger hooks in the new SDK (they did not in the old one),
    # so prevent_hooking_direct_calls is required to skip the one-shot blocking hook registered
    # above and let it only block the SetTitle call inside SetItemCardEx
    with prevent_hooking_direct_calls():
        this.SetTitle(
            item.GetManufacturer().FlashLabelName,
            item.GetShortHumanReadableName() + DT_SHIELD_NAME_SUFFIX,
            rarity_color_struct,
            item.GetZippyFrame(),
            item.GetElementalFrame(),
            item.IsReadied(),
        )


mod = build_mod(
    keybinds=[_memorize_shield_data],
    options=[_show_tips_option],
    hooks=[
        _copy_memorized_shield,
        _save_dt_shield,
        _load_dt_shield,
        _modify_item_card,
    ],
)
# Register the network functions so they are enabled/disabled together with the mod
add_network_functions(mod)
