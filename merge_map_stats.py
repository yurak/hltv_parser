#!/usr/bin/env python3
"""Merge CS2 and CS:GO map statistics into one file."""

import pandas as pd

def merge_map_stats(cs2_file="map_stats_cs2.csv", csgo_file="map_stats_csgo.csv", output_file="map_stats_combined.csv"):
    """
    Merge CS2 and CS:GO map statistics into one file.

    Args:
        cs2_file: Path to CS2 map statistics
        csgo_file: Path to CS:GO map statistics
        output_file: Path to combined output file
    """

    print("=" * 60)
    print("MERGING MAP STATISTICS")
    print("=" * 60)

    # Read CS2 data
    print(f"\nReading CS2 data from: {cs2_file}")
    try:
        df_cs2 = pd.read_csv(cs2_file)
        df_cs2['game_version'] = 'cs2'
        print(f"  ✓ Loaded {len(df_cs2)} CS2 records")
    except FileNotFoundError:
        print(f"  ✗ File not found: {cs2_file}")
        df_cs2 = pd.DataFrame()
    except Exception as e:
        print(f"  ✗ Error reading CS2 file: {e}")
        df_cs2 = pd.DataFrame()

    # Read CS:GO data
    print(f"\nReading CS:GO data from: {csgo_file}")
    try:
        df_csgo = pd.read_csv(csgo_file)
        df_csgo['game_version'] = 'csgo'
        print(f"  ✓ Loaded {len(df_csgo)} CS:GO records")
    except FileNotFoundError:
        print(f"  ✗ File not found: {csgo_file}")
        df_csgo = pd.DataFrame()
    except Exception as e:
        print(f"  ✗ Error reading CS:GO file: {e}")
        df_csgo = pd.DataFrame()

    # Combine dataframes
    if df_cs2.empty and df_csgo.empty:
        print("\n✗ No data to merge!")
        return None

    df_combined = pd.concat([df_cs2, df_csgo], ignore_index=True)

    # Reorder columns to have game_version near the front
    cols = df_combined.columns.tolist()
    if 'game_version' in cols:
        cols.remove('game_version')
        # Insert after player_name and map
        insert_idx = 2 if len(cols) >= 2 else len(cols)
        cols.insert(insert_idx, 'game_version')
        df_combined = df_combined[cols]

    # Save combined file
    df_combined.to_csv(output_file, index=False)

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"\nOutput file: {output_file}")
    print(f"  Total records: {len(df_combined)}")
    print(f"  CS2 records: {len(df_cs2)}")
    print(f"  CS:GO records: {len(df_csgo)}")
    print(f"  Unique players: {df_combined['player_name'].nunique()}")
    print(f"  Unique maps: {df_combined['map'].nunique()}")

    # Show distribution by game version and map
    print(f"\nRecords per game version:")
    version_counts = df_combined['game_version'].value_counts()
    for version, count in version_counts.items():
        print(f"  {version}: {count}")

    print(f"\nRecords per map (combined):")
    map_counts = df_combined['map'].value_counts().sort_index()
    for map_name, count in map_counts.items():
        print(f"  {map_name}: {count}")

    return output_file

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 4:
        merge_map_stats(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        merge_map_stats()
