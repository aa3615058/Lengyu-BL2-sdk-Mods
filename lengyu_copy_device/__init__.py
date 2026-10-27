from mods_base import ENGINE, EInputEvent, Mod, ObjectFlags, build_mod, hook
from unrealsdk import construct_object, find_enum, find_object
from unrealsdk.hooks import Block, Type, prevent_hooking_direct_calls
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from networking import add_network_functions, host

ENetMode = find_enum("ENetMode")

MOD_NAME: str = "Lengyu Copy Device"
TOOLTIP_NAME: str = "Copy"

mod: Mod | None = None

# WillowInventory.CreateInventoryFromSerialNumberString is a native static function, so it needs a
# WillowInventory object to be called on: either the CDO (Default__WillowInventory) or a blank
# template object works. It must only be fetched on first use - the game imports mods far too early,
# at which point the CDO may not exist yet and constructing an object is not safe either.
_template_inventory: UObject | None = None


def _get_template_inventory() -> UObject:
    """Get the object used to call static functions, looked up/constructed on first use"""
    global _template_inventory
    if _template_inventory is not None:
        return _template_inventory

    try:
        # Prefer the class default object
        _template_inventory = find_object("WillowInventory", "Default__WillowInventory")
    except ValueError:
        _template_inventory = None

    if _template_inventory is None:
        # Fallback: construct a blank template object under ENGINE (equivalent to the old
        # ConstructObject + KeepAlive). Note that Outer must not be None, otherwise the object is
        # invalid and any native function touching it crashes with an access violation.
        template = construct_object("WillowShield", ENGINE, "DefaultWillowShield", 1)
        # Outer is ENGINE (never collected), so adding KEEP_ALIVE to the template itself keeps it
        # from being garbage collected
        template.ObjectFlags |= ObjectFlags.KEEP_ALIVE
        _template_inventory = template

    return _template_inventory


def _copy_item(pc: UObject, item: UObject, price: int) -> None:
    item.GiveTo(pc.Pawn, False)
    pc.PlayerReplicationInfo.AddCurrencyOnHand(0, -price)


def _is_client() -> bool:
    """Whether this is a client in a multiplayer game (single player and host both return False)."""
    return ENGINE.GetCurrentWorldInfo().NetMode == ENetMode.NM_Client


def _create_and_copy_item(pc: UObject, serial_number: str, price: int) -> None:
    """Rebuild the item from its serial number string, give it to the player and take the money
    (this must be called synchronously at the needed moment, otherwise GiveTo happens after the UI
    refresh and the new item is only visible after reopening the inventory)."""
    # The function signature has a const out string parameter (read-only reference), so the SDK
    # wraps the return value into a tuple: (new item, echoed serial number string). So, just like
    # the old version, take [0].
    item = _get_template_inventory().CreateInventoryFromSerialNumberString(serial_number, pc.Pawn)[0]
    if item is None:
        return
    _copy_item(pc, item, price)


# Multiplayer core: the client sends the copy request to the host, which performs it.
# While running, func.sender is the PlayerReplicationInfo of the requesting player, so passing
# a PlayerID around manually (as the old version did) is no longer needed.
@host.json_message
def _server_copy_item(serial_number: str, price: int) -> None:
    pc = _server_copy_item.sender.Owner
    if pc is None or pc.Pawn is None:
        return
    _create_and_copy_item(pc, serial_number, price)


def _copy_key_hint(pc: UObject) -> str:
    """Return the copy key hint for the current input device
    (keyboard shows the actual bound key, gamepad is always LT)."""
    if pc.PlayerInput.bUsingGamepad:
        return "(LT)"
    return f"[{pc.PlayerInput.GetKeyForAction('UseSecondary', True)}]"


# Append the copy key hint to the tooltip text of the equipment/backpack page
@hook("WillowGame.StatusMenuInventoryPanelGFxObject:SetTooltipText", Type.PRE)
def _copy_device_tooltip(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    pc = this.ParentMovie.WPCOwner
    key = _copy_key_hint(pc)

    sep = "  " if this.bInEquippedView else "\n"
    # Calling SetTooltipText again here triggers this hook again, use
    # prevent_hooking_direct_calls to prevent the recursion
    with prevent_hooking_direct_calls():
        this.SetTooltipText(f"{args.TooltipsText}{sep}{key} {TOOLTIP_NAME}")
    return Block


@hook("WillowGame.StatusMenuInventoryPanelGFxObject:NormalInputKey", Type.PRE)
def _copy_device_input_key(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    if args.uevent != EInputEvent.IE_Pressed:
        return None

    if this.bInitialSetupFinished is False:
        return None

    if this.SwitchToQueuedInputHandler(args.ukey, args.uevent):
        return None

    pc = this.ParentMovie.WPCOwner
    pawn = pc.Pawn
    if pc is None or pawn is None:
        return None

    if pc.PlayerInput.bUsingGamepad:
        # Gamepad: Y keeps the original "drop" function (not blocked), copying moves to LT
        # (the old version blocked Y for copying, so pressing Y to drop threw away the original
        # item and then stuffed a copy into the inventory)
        if args.ukey != "XboxTypeS_LeftTrigger":
            return None
    elif args.ukey != pc.PlayerInput.GetKeyForAction("UseSecondary", True):
        return None

    if this.bInEquippedView is False:
        this.BackpackPanel.SaveState()

    item = this.GetSelectedThing()
    if this.CanDrop(item) is False:
        return Block

    price = item.GetMonetaryValue()
    rep_info = pc.PlayerReplicationInfo
    if price > rep_info.GetCurrencyOnHand(0):
        return Block

    item_copy = item.CreateClone()
    this.DropSelectedThing()
    # Refresh the interface tooltip text (internally this triggers the SetTooltipText hook above
    # again, so the tooltip is rebuilt correctly)
    this.ParentMovie.SetTooltipsText()
    if _is_client():
        # The client sends the copy request to the host, which performs it (the host then calls
        # GiveTo synchronously, and the item is replicated back with the copy)
        _server_copy_item(item_copy.GetSerialNumberString(), price)
    else:
        # Single player/host: same as the old version, finish GiveTo synchronously before
        # RestoreState so the list shows the item right away
        _create_and_copy_item(pc, item_copy.GetSerialNumberString(), price)

    if this.bInEquippedView is False:
        this.BackpackPanel.RestoreState()

    return Block


mod = build_mod(
    hooks=[
        _copy_device_tooltip,
        _copy_device_input_key,
    ],
)
# Register the network functions so they are enabled/disabled together with the mod
add_network_functions(mod)
