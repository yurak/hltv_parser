FIREPOWER  = ['kills_per_round','rounds_with_a_kill','kills_per_round_win','rating_1.0','damage_per_round','rounds_with_a_multi_kill','damage_per_round_win', 'pistol_round_rating']
ENTRYING = ['saved_by_teammate_per_round','traded_deaths_per_round','traded_deaths_percentage','opening_deaths_traded_percentage','assists_per_round','support_rounds']
TRADING = ['saved_teammate_per_round','trade_kills_per_round','trade_kills_percentage','assisted_kills_percentage','damage_per_kill']
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

MAP_INDEPENDENT = []