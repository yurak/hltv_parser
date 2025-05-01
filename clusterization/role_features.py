FIREPOWER  = ['kills_per_round','rounds_with_a_kill','kills_per_round_win','rating_1.0','damage_per_round','rounds_with_a_multi_kill','damage_per_round_win', 'pistol_round_rating']
ENTRYING = ['saved_by_teammate_per_round','traded_deaths_per_round','traded_deaths_percentage','opening_deaths_traded_percentage','assists_per_round','support_rounds']
TRADING = ['saved_teammate_per_round','trade_kills_per_round','trade_kills_percentage','assisted_kills_percentage','damage_per_kill', 'saved_by_teammate_per_round']
OPENING = ['opening_kills_per_round','opening_deaths_per_round','opening_attempts','opening_success','win_after_opening_kill','attacks_per_round']
CLUTCHING = ['clutch_points_per_round','last_alive_percentage','1on1_win_percentage','time_alive_per_round','saves_per_round_loss']
SNIPING = ['sniper_kills_per_round','sniper_kills_percentage','rounds_with_sniper_kills_percentage','sniper_multi_kill_rounds','sniper_opening_kills_per_round']
UTILITY = ['utility_damage_per_round','utility_kills_per_100_rounds','flashes_thrown_per_round','flash_assists_per_round','time_opponent_flashed_per_round']
INTEGRAL = ['sniping', 'trading', 'clutching', 'utility', 'firepower', 'opening', 'entrying']

MAIN_COMPONENTS_MAP = {
                        'firepower': FIREPOWER,
                        'entrying': ENTRYING, 
                        'trading': TRADING, 
                        'opening': OPENING, 
                        'clutching': CLUTCHING,
                        'sniping': SNIPING,
                        'utility': UTILITY
}

MAP_INDEPENDENT = ['win_after_opening_kill','traded_deaths_percentage', 'traded_deaths_per_round', 'trade_kills_percentage', 'trade_kills_per_round', 'time_alive_per_round',
                   'support_rounds', 'saved_teammate_per_round', 'saved_by_teammate_per_round',
                   'rounds_with_a_kill', 'rounds_with_a_multi_kill', 'kills_per_round_win', 'kills_per_round', 'flashes_thrown_per_round'
]

CS_MAPS = ['de_train', 'de_nuke', 'de_inferno', 'de_mirage', 'de_dust2', 'de_vertigo','de_ancient', 'de_anubis']


PLAYERS_TOP20_SOURCE = 'players_top20.csv'

TEAM_MAP = {
            'navi': ['b1t', 'iM', 'Aleksib', 'jL', 'w0nderful'],
            'vitality': ['ZywOo', 'flameZ', 'ropz', 'mezii', 'apEX']
        }