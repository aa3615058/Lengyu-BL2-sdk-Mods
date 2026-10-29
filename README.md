# Lengyu-BL2-sdk-Mods

A collection of Borderlands 2 mods developed by Lengyu based on [willow-sdk](https://github.com/bl-sdk/willow2-mod-manager).

Every mod is distributed as a `.sdkmod` package: drop it into your `sdk_mods` folder and enable it in the Mods menu.

## Content

### [Death Trap Memory](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/death_trap_memory/death_trap_memory.sdkmod)

- Adds a memory expansion program to Death Trap.
- Press the keybind (default: 6) to save the data of your equipped shield. The next time you summon Death Trap, if that shield is in your backpack, Death Trap copies it, otherwise it behaves like the vanilla game.
- Leave the shield slot empty and press the keybind to clear the memory.
- The memory is persistent and stored per save game.
- Works in multiplayer games, requires both the host and the client to install this mod.

### [Fill Up Ammo](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/fillup_ammo/fillup_ammo.sdkmod)

- Refills all of your ammo at the ammo vending machine with a single keybind.
- Every ammo type can be toggled separately in the mod options, and if you don't have enough money it buys as much as it can.
- Works in multiplayer games.

### [Lengyu Copy Device](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/lengyu_copy_device/lengyu_copy_device.sdkmod)

- Now you can copy equipment. Press the Interact key on the Equipment or Backpack page to drop and copy the selected equipment.
- Copying costs money equal to the selling price of the equipment.
- Gamepad players: press Left Trigger (LT) to copy, Y keeps the vanilla drop function.
- Works in multiplayer games, requires both the host and the client to install this mod.

### [Lengyu TP Device](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/lengyu_tp_device/lengyu_tp_device.sdkmod)

- Allows you to teleport yourself anywhere you marked.
- Press numpad 0 to mark the current location and numpad dot to teleport back to it. 3 slots are supported, switch them with numpad 1, 2, 3.
- Press numpad 4, 5, 6 to teleport yourself next to another player.
- Optionally prints the teleport console command to `python-sdk.log`.
- Works in multiplayer games. Cannot be used in the Digistruct Peak map.

### [Loot Collector](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/loot_collector/loot_collector.sdkmod)

- Teleports all loot on the map to you, arranged in a circle around you and sorted by rarity (keybind: `/`).
- Deletes all white and green loot on the map (keybind: numpad minus).
- Deletes all loot on the map (keybind: Delete). Use with caution.
- Mission items, unpickupable items and ECHOs are all excluded.
- In multiplayer games, non-host players can only use the collect loot function.

### [Mission Repeatable](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/mission_repeatable/mission_repeatable.sdkmod)

- Makes the side missions that reward the following gear repeatable: Fibber, Pimpernel, Swordsplosion, Kitten, Heartbreaker, Rubi, Lady Fist, Amigo Sincero, Hail, Creamer, Evolve Varkid, Chere-amie, Orc and Sand Hawk. Love Thumper and Treasure of the Sands are supported as well.
- Every mission can be toggled in the mod options.
- About Sand Hawk: the reward of "I Know It When I See It" is changed to the Sand Hawk, the mission becomes repeatable, and "Don't Copy That Floppy" no longer requires completing it first.

### [Weapon Switcher Q](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/weapon_switcher_q/weapon_switcher_q.sdkmod)

- Press Q to switch back to your last used weapon, like in Counter-Strike and many other FPS games.

### [Shop Reseter](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/shop_reseter/shop_reseter.sdkmod)

- Press F9 after leaving a vending machine to reset the shop you last used.
- Works in multiplayer games, the host player does not need this mod. In TPS multiplayer only the host player can use it.

### [Throw Weapon Then Pickup](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/throw_weapon_then_pickup/throw_weapon_then_pickup.sdkmod)

- Press H to throw your current weapon and then pick it back up immediately, done with internal functions.
- Instant reload with no reloading animation, Gaige can also reload this way.
- Instant weapon swap with no holstering animation, e.g. sniper into Lady Fist, Flakker into Ahab, Sand Hawk + Bee into Amigo Sincero.


### [Simple Chinese Fix](https://raw.githubusercontent.com/aa3615058/Lengyu-BL2-sdk-Mods/main/simple_chinese_fix/simple_chinese_fix.sdkmod)

- Fixes a few Tianmiao Chinese localization entries that mysteriously stopped working in version 1.8.5.
- Not needed for players using the official translation.