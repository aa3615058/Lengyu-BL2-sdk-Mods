import math

from mods_base import ENGINE, BoolOption, EInputEvent, Game, Mod, build_mod, get_pc, hook
from unrealsdk import find_enum
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from networking import add_network_functions, host

ENetMode = find_enum("ENetMode")

# Shop item name of the ammo box in the vending machine: (ammo pool resource name, ammo per box, option name)
AMMO_DICT: dict[str, tuple[str, int, str]] = {
    # Pistol
    "AmmoShop_Repeater_Pistol_Clip": ("Ammo_Repeater_Pistol", 54, "Pistol"),
    # Assault rifle
    "AmmoShop_Assault_Rifle_Bullets": ("Ammo_Combat_Rifle", 54, "Assault Rifle"),
    # Shotgun
    "AmmoShop_Shotgun_Shells": ("Ammo_Combat_Shotgun", 24, "Shotgun"),
    # SMG
    "AmmoShop_Patrol_SMG_Clip": ("Ammo_Patrol_SMG", 72, "SMG"),
    # Sniper rifle
    "AmmoShop_Sniper_Rifle_Cartridges": ("Ammo_Sniper_Rifle", 18, "Sniper Rifle"),
    # Grenade
    "AmmoShop_Grenade_Protean": ("Ammo_Grenade_Protean", 3, "Grenade"),
    # Laser (TPS only)
    "AmmoShop_Laser_Cells": ("Ammo_Combat_Laser", 68, "Laser"),
    # Rocket launcher
    "AmmoShop_Rocket_Launcher": ("Ammo_Rocket_Launcher", 12, "Rocket Launcher"),
}

mod: Mod | None = None


def _is_client() -> bool:
    """Whether this is a client in a multiplayer game (single player and host both return False)."""
    return ENGINE.GetCurrentWorldInfo().NetMode == ENetMode.NM_Client


def _find_ammo_pool(pc: UObject, pool_name: str) -> UObject | None:
    for pool in pc.ResourcePoolManager.ResourcePools:
        if pool is None:
            continue
        if (
            pool.Class.Name != "AmmoResourcePool"
            and pool.Definition.Resource.Name != "Ammo_Grenade_Protean"
        ):
            continue
        if pool.Definition.Resource.Name == pool_name:
            return pool
    return None


def _find_shop_item(vm: UObject, ammo_item: str) -> UObject | None:
    """Check whether the vending machine sells this kind of ammo, return the matching shop item"""
    for item in vm.ShopInventory:
        try:
            if item.DefinitionData.ItemDefinition.Name == ammo_item:
                return item
        except AttributeError:
            continue
        except Exception:  # noqa: BLE001
            break
    return None


def _apply_fill_up(rep_info: UObject, pool: UObject, cost: int, value: int) -> None:
    pool.SetCurrentValue(value)
    rep_info.AddCurrencyOnHand(0, -cost)


# Multiplayer core: the client sends the refill request to the host, which performs it
# (when the host calls it itself, it runs locally right away).
# While running, func.sender is the PlayerReplicationInfo of the requesting player, so passing
# a PlayerID around manually (as the old version did) is no longer needed.
@host.json_message
def _fill_up_ammo_on_host(pool_name: str, cost: int, value: int) -> None:
    pc = _fill_up_ammo_on_host.sender.Owner
    if pc is None:
        return

    pool = _find_ammo_pool(pc, pool_name)
    if pool is None:
        return

    _apply_fill_up(pc.PlayerReplicationInfo, pool, cost, value)


def _make_ammo_options() -> dict[str, BoolOption]:
    options: dict[str, BoolOption] = {}
    # Ammo types that are disabled by default
    default_disabled: set[str] = {"Rocket Launcher"}
    for data in AMMO_DICT.values():
        option_name = data[2]
        # Lasers only exist in TPS
        if option_name == "Laser" and Game.get_current() != Game.TPS:
            continue
        options[option_name] = BoolOption(
            identifier=option_name,
            value=option_name not in default_disabled,
            description=(
                f"When enabled, Fill Up Ammo includes {option_name} ammo. When disabled, {option_name} ammo is skipped."
            ),
        )
    return options


_ammo_options: dict[str, BoolOption] = _make_ammo_options()

# Fill up ammo - interface display
@hook("WillowGame.VendingMachineExGFxMovie:SetTooltips", Type.PRE)
def _fill_up_ammo_tooltips(
    this: UObject,
    _args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    if this.VM.GetShopType() != 1:
        return None
    if not (
        (this.CurrentSelectionItem is None and this.bOnItemOfTheDay)
        or (not this.IsCurrentSelectionSell() and not this.IsCurrentSelectionBuyBack())
    ):
        return None

    pc = get_pc()
    if pc.PlayerInput.bUsingGamepad:
        purchase_key, fill_key, trash_key = "(A)", "(Y)", "(L)"
        compare_key, sort_key, inspect_key, cancel_key = "(X)", "(LT)/(RT)", "(R)", "(B)"
    else:
        fill_key = f"[{pc.PlayerInput.GetKeyForAction('UseSecondary', True)}]"
        purchase_key, trash_key = "[Enter]", "[Del]"
        compare_key, sort_key, inspect_key, cancel_key = (
            "[E]",
            "[Page Up]/[Page Down]",
            "[F]",
            "[Esc]",
        )

    this.TwoPanelInterface.SetTooltipText(
        "   ".join(
            [
                f"{purchase_key} Buy",
                f"{fill_key} Fill Up Ammo",
                f"{trash_key} Sell Junk",
                f"{compare_key} Compare",
                f"{sort_key} Sort",
                f"{inspect_key} Inspect",
                f"{cancel_key} Cancel",
            ],
        ),
    )
    # Replace the original SetTooltips with the text that includes the fill up ammo hint
    return Block


# Fill up ammo - input handling
@hook("WillowGame.VendingMachineExGFxMovie:MainInputKey", Type.PRE)
def _fill_up_ammo_input_key(
    this: UObject,
    args: WrappedStruct,
    _ret: object,
    _func: BoundFunction,
) -> type[Block] | None:
    if args.uevent != EInputEvent.IE_Pressed:
        return None

    pc = get_pc()
    if pc.PlayerInput.bUsingGamepad:
        if args.ukey != "XboxTypeS_Y":
            return None
    elif args.ukey != pc.PlayerInput.GetKeyForAction("UseSecondary", True):
        return None

    vm = this.VM
    if vm.GetShopType() != 1:
        return None
    if not (
        (this.CurrentSelectionItem is None and this.bOnItemOfTheDay)
        or (not this.IsCurrentSelectionSell() and not this.IsCurrentSelectionBuyBack())
    ):
        return None

    rep_info = pc.PlayerReplicationInfo
    wallet = rep_info.GetCurrencyOnHand(0)
    alert_value = 0

    for ammo_item, (pool_name, box_capacity, option_name) in AMMO_DICT.items():
        # Check the ammo type option switch
        option = _ammo_options.get(option_name)
        if option is None or not option.value:
            continue

        # Check whether the vending machine sells this kind of ammo
        shop_item = _find_shop_item(vm, ammo_item)
        if shop_item is None:
            continue

        # Check whether the ammo is already full
        pool = _find_ammo_pool(pc, pool_name)
        if pool is None:
            continue
        max_ammo = int(pool.GetMaxValue())
        if pool.GetCurrentValue() == max_ammo:
            continue

        # Buy ammo
        price = vm.GetSellingPriceForInventory(shop_item, pc, 1)  # Unit price of one ammo box
        total_cost = price * math.ceil((max_ammo - pool.GetCurrentValue()) / box_capacity)
        if wallet >= total_cost:
            # Enough money, buy it full
            cost, value = total_cost, max_ammo
            alert_value = max(alert_value, 1)
        else:
            # Not enough money, buy as much as possible
            amount = math.floor(wallet / price)
            cost, value = amount * price, pool.GetCurrentValue() + amount * box_capacity
            alert_value = max(alert_value, 2)

        if _is_client():
            _fill_up_ammo_on_host(pool_name, cost, value)
        else:
            _apply_fill_up(rep_info, pool, cost, value)
        wallet -= cost

    if alert_value == 0:
        # Ammo is already full
        this.PlayFeedback_CannotCarryOrUse()
    elif alert_value == 2:
        # Not enough funds
        this.PlayFeedback_CannotAfford()
    else:
        # Purchase succeeded
        this.PlayUISound("Buy")
        this.Feedback.TriggerPurchased()

    return Block


mod = build_mod(
    hooks=[
        _fill_up_ammo_tooltips,
        _fill_up_ammo_input_key,
    ],
    options=list(_ammo_options.values()),
)
# Register the network functions so they are enabled/disabled together with the mod
add_network_functions(mod)
