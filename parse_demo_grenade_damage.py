"""
Parse CS2 demo file to extract grenade damage per player.

Usage:
    python3 parse_demo_grenade_damage.py <path_to_demo.dem> [--player "nickname"]
"""

import sys
import argparse
from demoparser2 import DemoParser

GRENADE_WEAPONS = {
    "hegrenade",
    "molotov",
    "incgrenade",
    "inferno",       # molotov/incgrenade active fire entity
}


def parse_grenade_damage(demo_path, player_filter=None):
    parser = DemoParser(demo_path)

    # Parse player_hurt events — contains attacker, victim, weapon, damage
    result = parser.parse_events(["player_hurt"])
    _, df = result[0]
    events = df.to_dict("records")

    if not events:
        print("No player_hurt events found in this demo.")
        return

    # Collect grenade damage: {victim_name: {weapon: total_damage}}
    damage_received = {}
    damage_dealt = {}

    for event in events:
        weapon = event.get("weapon", "").lower()
        if weapon not in GRENADE_WEAPONS:
            continue

        # Normalize molotov variants
        display_weapon = "molotov/incgrenade" if weapon in ("molotov", "incgrenade", "inferno") else weapon

        dmg = event.get("dmg_health", 0) or event.get("damage", 0) or 0
        victim = event.get("user_name", "unknown")
        attacker = event.get("attacker_name", "unknown")

        # Damage received
        if victim not in damage_received:
            damage_received[victim] = {}
        damage_received[victim][display_weapon] = damage_received[victim].get(display_weapon, 0) + dmg

        # Damage dealt
        if attacker not in damage_dealt:
            damage_dealt[attacker] = {}
        damage_dealt[attacker][display_weapon] = damage_dealt[attacker].get(display_weapon, 0) + dmg

    # Print results
    def print_table(title, data, filter_name=None):
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

        players = sorted(data.keys(), key=lambda p: sum(data[p].values()), reverse=True)

        if filter_name:
            players = [p for p in players if filter_name.lower() in p.lower()]
            if not players:
                print(f"  Player '{filter_name}' not found.")
                return

        for player in players:
            weapons = data[player]
            total = sum(weapons.values())
            print(f"\n  {player}: {total} total grenade damage")
            for w, d in sorted(weapons.items(), key=lambda x: x[1], reverse=True):
                print(f"    {w:25s} {d:>5d} hp")

    print_table("GRENADE DAMAGE RECEIVED (by victim)", damage_received, player_filter)
    print_table("GRENADE DAMAGE DEALT (by attacker)", damage_dealt, player_filter)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    all_victims = sorted(damage_received.keys(), key=lambda p: sum(damage_received[p].values()), reverse=True)
    if player_filter:
        all_victims = [p for p in all_victims if player_filter.lower() in p.lower()]

    print(f"\n  {'Player':<25s} {'Received':>10s} {'Dealt':>10s}")
    print(f"  {'-'*25} {'-'*10} {'-'*10}")
    all_players = set(damage_received.keys()) | set(damage_dealt.keys())
    if player_filter:
        all_players = {p for p in all_players if player_filter.lower() in p.lower()}

    for player in sorted(all_players, key=lambda p: sum(damage_received.get(p, {}).values()), reverse=True):
        recv = sum(damage_received.get(player, {}).values())
        dealt = sum(damage_dealt.get(player, {}).values())
        print(f"  {player:<25s} {recv:>10d} {dealt:>10d}")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Parse CS2 demo for grenade damage")
    arg_parser.add_argument("demo", help="Path to .dem file")
    arg_parser.add_argument("--player", "-p", help="Filter by player name (partial match)", default=None)
    args = arg_parser.parse_args()

    parse_grenade_damage(args.demo, args.player)
