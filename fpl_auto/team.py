import pandas as pd
import fpl_auto.data as fpl

POSITIONS = ['GK', 'DEF', 'MID', 'FWD']
MAX_PER_POS = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
MIN_PRICE = {'GK': 4.0, 'DEF': 4.0, 'MID': 4.5, 'FWD': 4.5}
SQUAD_SIZE = 15
XI_SIZE = 11


class Team:
    def __init__(
        self, season, gameweek=1, budget=100.0, transfers_left=0,
        players=None, chips_used=None, transfer_history=None,
        triple_captain_available=True, bench_boost_available=True,
        free_hit_available=True, wildcard_available=True, free_hit_team=None,
        purchase_prices=None, strategy_config=None,
    ):
        players = players if players is not None else [[], [], [], [], []]
        chips_used = chips_used if chips_used is not None else []
        transfer_history = transfer_history if transfer_history is not None else []

        self.fpl = fpl.get_fpl_data('data', season)
        self.season = season
        self.gameweek = gameweek
        self.budget = budget
        self.purchase_prices = dict(purchase_prices) if purchase_prices is not None else {}
        self.hits_taken = 0
        self.transfer_budget_spent = 0  # Reset per GW: tracks cumulative xP gain budget used
        self.strategy_config = strategy_config  # Store strategy config for access in auto_transfer()

        self.gks  = list(players[0])
        self.defs = list(players[1])
        self.mids = list(players[2])
        self.fwds = list(players[3])
        self.subs = list(players[4])

        self.free_hit_team = free_hit_team

        # From 2024-25, transfer cap was removed
        if self.season == '2024-25':
            self.transfers_left = transfers_left
        else:
            self.transfers_left = min(transfers_left, 2)

        self.chips_used = chips_used
        self.transfer_history = transfer_history
        self.chip_triple_captain_available = triple_captain_available
        self.chip_triple_captain_active = False
        self.chip_bench_boost_available = bench_boost_available
        self.chip_bench_boost_active = False
        self.chip_free_hit_available = free_hit_available
        self.chip_free_hit_active = False
        self.chip_wildcard_available = wildcard_available

        self.gw_data = self.fpl.get_gw_data(self.season, self.gameweek)

        if not self.chip_wildcard_available and self.gameweek == 19:
            print('============== Wildcard Returned! ==============\n')
            self.chip_wildcard_available = True

        self.gk_xp  = self.fpl.get_predictions(self.gameweek, 'GK')
        self.def_xp = self.fpl.get_predictions(self.gameweek, 'DEF')
        self.mid_xp = self.fpl.get_predictions(self.gameweek, 'MID')
        self.fwd_xp = self.fpl.get_predictions(self.gameweek, 'FWD')
        self.combined_xp = [self.gk_xp, self.def_xp, self.mid_xp, self.fwd_xp]

        self.all_xp = self._get_n_gws_xp(5, discount_factor=0.8)

        self.player_list = self.fpl.player_list
        self._pos_player_lists = {pos: self._generate_player_list(pos) for pos in POSITIONS}

        # Single-GW xP — used only for suggest_subs (bench weakest for next game)
        self._xp_dicts = {
            'GK':  dict(zip(self.gk_xp.Name,  self.gk_xp.xP)),
            'DEF': dict(zip(self.def_xp.Name, self.def_xp.xP)),
            'MID': dict(zip(self.mid_xp.Name, self.mid_xp.xP)),
            'FWD': dict(zip(self.fwd_xp.Name, self.fwd_xp.xP)),
        }
        # Multi-GW discounted xP — used for captain, transfers, chips
        self._all_xp_dicts = {
            pos: dict(zip(df.Name, df.xP))
            for pos, df in zip(POSITIONS, self.all_xp)
        }

        self.prev_pos_list = self.fpl.position_dict(self.gameweek - 1)
        self._pos_cache: dict = {}  # player -> position, populated lazily

        self.captain = ''
        self.vice_captain = ''

        try:
            self.recent_gw = self.fpl.get_recent_gw() - 1
        except Exception:
            self.recent_gw = 38

        if self.gameweek >= self.recent_gw and self.season == '2023-24':
            self.positions_list = self.fpl.position_dict(self.recent_gw)
            self.points_scored = self.fpl.actual_points_dict(season, self.recent_gw - 1)
        elif self.gameweek == 8 and self.season == '2023-24':
            self.positions_list = self.fpl.position_dict(self.gameweek)
            self.points_scored = self.fpl.actual_points_dict(season, self.gameweek)
        else:
            self.positions_list = self.fpl.position_dict(self.gameweek - 1)
            self.points_scored = self.fpl.actual_points_dict(season, self.gameweek)

        self.player_stop_list = []

        if self.free_hit_team is not None and self.free_hit_team[2] == self.gameweek - 1:
            self._load_free_hit_team()

    # ------------------------------------------------------------------
    # Position helpers — eliminate repetitive 4-branch code everywhere
    # ------------------------------------------------------------------

    def _pos_squad_list(self, pos: str) -> list:
        if pos == 'GK':  return self.gks
        if pos == 'DEF': return self.defs
        if pos == 'MID': return self.mids
        return self.fwds

    def _all_xi_players(self):
        """Yields (name, pos) for every starting XI player."""
        for pos in POSITIONS:
            for p in self._pos_squad_list(pos):
                yield p, pos

    def _all_squad_players(self):
        """Yields (name, pos) for every player including subs."""
        yield from self._all_xi_players()
        for sub in self.subs:
            yield sub[0], sub[1]

    # ------------------------------------------------------------------
    # Squad validation
    # ------------------------------------------------------------------

    def check_violate_club_rule(self, player, club_counts=None):
        player_club = self.fpl.get_player_team(player, self.gameweek, self.gw_data)
        if club_counts is None:
            club_counts = self.get_club_counts(self.gw_data)
        try:
            club_counts[player_club] = club_counts.get(player_club, 0) + 1
            return club_counts[player_club] > 3
        except TypeError:
            return False

    def transfer_in_allowed(self, player, position='none', custom_price=None, club_counts=None, effective_budget=None, replacing=False):
        p_cost = custom_price if custom_price is not None else self.player_value(player, self.gw_data)
        if position == 'none':
            position = self.player_pos(player)

        if player in self.player_stop_list:
            return False
        if position not in POSITIONS:
            return False
        if p_cost is None:
            return False
        if player not in self.player_list:
            return False
        if self.player_in_squad(player):
            return False

        if club_counts is None:
            club_counts = self.get_club_counts(self.gw_data)
        player_club = str(self.fpl.get_player_team(player, self.gameweek, self.gw_data))
        if club_counts.get(player_club, 0) + 1 > 3 and player_club != 'None':
            return False

        if not replacing and len(self._pos_squad_list(position)) >= MAX_PER_POS[position]:
            return False
        available = effective_budget if effective_budget is not None else self.budget
        if available < p_cost:
            return False
        if not replacing and self.squad_size() >= SQUAD_SIZE:
            return False
        return True

    # ------------------------------------------------------------------
    # Squad mutation
    # ------------------------------------------------------------------

    def add_player(self, player, position='none', custom_price=None, force=False):
        if not self.transfer_in_allowed(player, position, custom_price):
            return None
        p_cost = custom_price if custom_price is not None else self.player_value(player, self.gw_data)
        if position == 'none':
            position = self.player_pos(player)
        self._pos_squad_list(position).append(player)
        self.budget -= p_cost
        self.purchase_prices[player] = p_cost

    def remove_player(self, player, position):
        self.return_subs_to_team()
        self._pos_squad_list(position).remove(player)
        self.budget += self.selling_price(player)
        self.purchase_prices.pop(player, None)

    def add_sub(self, player, position):
        try:
            self._pos_squad_list(position).remove(player)
        except ValueError:
            pass

    def remove_sub(self, player, position):
        self._pos_squad_list(position).append(player)

    def return_subs_to_team(self):
        for sub in self.subs:
            self.remove_sub(sub[0], sub[1])
        self.subs = []

    def return_player_to_team(self, player, position):
        self._pos_squad_list(position).append(player)

    # ------------------------------------------------------------------
    # Substitutions
    # ------------------------------------------------------------------

    def suggest_subs(self):
        if self.squad_size() != SQUAD_SIZE:
            print(f'Error: Squad has not been filled up (Size {self.squad_size()})')
            self.remove_excess_players()

        self.return_subs_to_team()

        ranked_gk = sorted(
            [[p, self._xp_dicts['GK'].get(p, 0), 'GK'] for p in self.gks],
            key=lambda x: float(x[1]),
        )
        ranked_others = sorted(
            [[p, self._xp_dicts[pos].get(p, 0), pos]
             for pos in ('DEF', 'MID', 'FWD')
             for p in self._pos_squad_list(pos)],
            key=lambda x: float(x[1]),
        )

        # Defensive check: ensure we have at least one GK before accessing
        if not ranked_gk:
            return []

        subs = [[ranked_gk[0][0], 'GK']]
        positions_substituted = {'GK': 1}
        for player in ranked_others:
            if positions_substituted.get(player[2], 0) < 2 and len(subs) < 4:
                subs.append([player[0], player[2]])
                positions_substituted[player[2]] = positions_substituted.get(player[2], 0) + 1
        return subs

    def make_subs(self, subs):
        self.subs = subs
        for sub in subs:
            self.add_sub(sub[0], sub[1])

    def auto_subs(self):
        self.return_subs_to_team()
        self.make_subs(self.suggest_subs())

    # ------------------------------------------------------------------
    # Expected points
    # ------------------------------------------------------------------

    def player_xp(self, player, position):
        if position is None:
            position = self.player_pos(player)
        return self._all_xp_dicts[position].get(player, 0)

    def get_all_xp(self, include_subs=False):
        result = [
            [p, self._all_xp_dicts[pos].get(p, 0) * (2 if p == self.captain else 1)]
            for p, pos in self._all_xi_players()
        ]
        if include_subs:
            result += [[s[0], self._all_xp_dicts[s[1]].get(s[0], 0)] for s in self.subs]
        return result

    def team_xp(self, include_subs=False):
        if self.season == '2022-23' and self.gameweek == 7:
            return 0

        self.return_subs_to_team()
        self.auto_subs()
        self.auto_captain()

        if self.squad_size() != SQUAD_SIZE:
            print(f'Team not complete, squad size {self.squad_size()}')
            self.return_subs_to_team()
            self.remove_excess_players()
            return 0

        total = sum(
            self._all_xp_dicts[pos].get(p, 0) * (2 if p == self.captain else 1)
            for p, pos in self._all_xi_players()
        )
        if include_subs:
            total += sum(self._all_xp_dicts[s[1]].get(s[0], 0) for s in self.subs)
        return total

    # ------------------------------------------------------------------
    # Actual points
    # ------------------------------------------------------------------

    def player_p(self, player, position):
        if player not in self.points_scored:
            return 0
        raw = self.points_scored[player]
        captain_played = self.captain_played()
        if self.captain == player and captain_played:
            multiplier = 3 if self.chip_triple_captain_active else 2
            return raw * multiplier
        if self.vice_captain == player and not captain_played:
            return raw * 2
        return raw

    def captain_played(self):
        return self.points_scored.get(self.captain, 0) != 0

    def team_p(self, include_subs=False):
        if self.season == '2022-23' and self.gameweek == 7:
            return 0
        if self.season == '2023-24' and self.gameweek > self.recent_gw:
            return 0

        self.return_subs_to_team()
        self.auto_subs()
        self.auto_captain()
        self.swap_players_who_didnt_play()

        total = sum(self.player_p(p, pos) for p, pos in self._all_xi_players())
        if include_subs:
            total += sum(self.player_p(sub[0], sub[1]) for sub in self.subs)
        if self.chip_bench_boost_active:
            total += sum(self.player_p(sub[0], sub[1]) for sub in self.subs)
        total -= 4 * self.hits_taken
        return total

    def team_p_list(self, include_subs=False):
        captain_played = self.captain_played()
        result = []
        for p, pos in self._all_xi_players():
            label = f'(C) {p}' if p == self.captain and captain_played else \
                    f'(VC) {p}' if p == self.vice_captain and not captain_played else p
            result.append([label, pos, self.player_p(p, pos)])
        if include_subs:
            result += [[sub[0], sub[1], self.player_p(sub[0], sub[1])] for sub in self.subs]
        return result

    def team_xp_list(self):
        self.auto_subs()
        return [
            [f'(C) {p}' if p == self.captain else p, pos,
             self.player_xp(p, pos) * (2 if p == self.captain else 1)]
            for p, pos in self._all_xi_players()
        ]

    def p_list(self):
        return [pts for _, _, pts in self.team_p_list()]

    # ------------------------------------------------------------------
    # Captain
    # ------------------------------------------------------------------

    def suggest_captaincy(self):
        xp_list = sorted(self.get_all_xp(), key=lambda x: float(x[1]), reverse=True)
        if len(xp_list) < 2:
            raise ValueError(f'Need at least 2 players to suggest captaincy, squad has {self.squad_size()}')
        return xp_list[0], xp_list[1]

    def update_captain(self, captain, vice_captain):
        self.captain = captain
        self.vice_captain = vice_captain

    def auto_captain(self):
        captain, vice_captain = self.suggest_captaincy()
        self.update_captain(captain[0], vice_captain[0])

    # ------------------------------------------------------------------
    # Transfers
    # ------------------------------------------------------------------

    def suggest_transfer_out(self):
        xp_list = sorted(self.get_all_xp(include_subs=True), key=lambda x: float(x[1]))
        for name, _ in xp_list:
            pos = self.player_pos(name)
            budget = self.selling_price(name)
            if pos is not None and budget:
                return name, pos, budget
        print('No player found to transfer out')
        return '', '', 0

    def suggest_transfer_in(self, position, out_player, budget):
        player_xp_list = self.all_xp[POSITIONS.index(position)]
        player_xp_list = player_xp_list.sort_values(by='xP', ascending=False).values.tolist()
        player_xp_list = [p for p in player_xp_list if p[1] >= 3]
        out_xp = self._all_xp_dicts[position].get(out_player, 0)

        # Pre-compute once — reused for every candidate in this search
        club_counts = self.get_club_counts(self.gw_data)
        gw_prices = self.gw_data[['value']].to_dict()['value']

        for player in player_xp_list:
            name, p_xp = player[0], player[1]
            xp_gain = p_xp - out_xp
            if xp_gain < 2:
                continue
            if name == out_player or self.player_in_squad(name):
                continue
            p_cost = gw_prices.get(name)
            if p_cost is None:
                continue
            p_cost /= 10
            if p_cost > budget:
                continue
            if self.transfer_in_allowed(name, position, p_cost, club_counts=club_counts, effective_budget=budget, replacing=True):
                return name

        return 'No player found to transfer in'

    def player_in_squad(self, player):
        name = player[0] if isinstance(player, list) else player
        return any(name in self._pos_squad_list(pos) for pos in POSITIONS)

    def transfer(self, transfer_out, transfer_in, position, threshold=4):
        try:
            out_xp = self.player_xp(transfer_out, position)
            in_xp = self.player_xp(transfer_in, position)
            xp_gain = in_xp - out_xp

            if xp_gain < threshold:
                return

            self.return_subs_to_team()
            self.remove_player(transfer_out, position)
            self.add_player(transfer_in, position)

            if self.squad_size() == 14:
                self.add_player(transfer_out, position, force=True)
            elif self.squad_size() == 16:
                self.remove_player(transfer_in, position)
            else:
                print(f'TRANSFER: OUT {transfer_out} {position} --> IN {transfer_in} {position} | xP Gain: {xp_gain:.2f}\n')
                if self.transfers_left <= 0:
                    self.hits_taken += 1
                self.transfers_left -= 1
                self.transfer_history.append([self.gameweek, [transfer_out, transfer_in], round(xp_gain, 2)])
        except ValueError:
            pass

    def auto_transfer(self, strategy_config=None, threshold=None):
        """Apply transfer heuristic with optional strategy config constraints.

        Args:
            strategy_config: Optional StrategyConfig instance with transfer constraints.
                If None, uses backward-compatible defaults (threshold=4, no budget/window constraints).
            threshold: Optional xP improvement threshold (ignored if strategy_config provided).
        """
        print('Checking for any transfers...', end='\r')
        if self.season == '2022-23' and self.gameweek == 7:
            return
        if self.season == '2023-24' and self.gameweek > self.recent_gw:
            return
        if self.gameweek > 35:
            return
        if self.transfers_left <= 0:
            return

        # Initialize or extract strategy config
        if strategy_config is None:
            # Backward compat: use old default threshold, no constraints
            use_budget_constraint = False
            use_window_constraint = False
            xp_threshold = threshold or 4
            threshold_mode = 'absolute'
        else:
            # New path: use config
            use_budget_constraint = True
            use_window_constraint = strategy_config.transfer_window_gw_range is not None
            xp_threshold = strategy_config.transfer_xp_threshold
            threshold_mode = strategy_config.transfer_xp_threshold_mode

        # Add window gate (early return if outside window)
        if use_window_constraint:
            gw_min, gw_max = strategy_config.transfer_window_gw_range
            if not (gw_min <= self.gameweek <= gw_max):
                # Log diagnostic
                print(f"[GW{self.gameweek}] Transfer window inactive (window={gw_min}-{gw_max}); skipping auto_transfer()")
                return

        # Loop over available transfers with budget check
        for transfer_num in range(self.transfers_left):
            # Check budget constraint
            if use_budget_constraint:
                transfer_budget_remaining = strategy_config.transfer_budget_per_gw - self.transfer_budget_spent
                if transfer_budget_remaining <= 0:
                    print(f"[GW{self.gameweek}] Transfer budget exhausted ({self.transfer_budget_spent:.1f}/{strategy_config.transfer_budget_per_gw:.1f}); stopping transfers")
                    break

            out, pos, budget = self.suggest_transfer_out()
            if pos == '':
                return
            if budget + self.budget < MIN_PRICE[pos]:
                return
            transfer_in = self.suggest_transfer_in(pos, out, self.budget + budget)

            if transfer_in == 'No player found to transfer in':
                break

            xp_in = self.player_xp(transfer_in, pos)
            xp_out = self.player_xp(out, pos)
            xp_gain = xp_in - xp_out

            # Apply threshold logic (relative or absolute)
            if threshold_mode == 'relative':
                # Relative improvement: (new - old) / old > threshold
                # Safeguard: if xp_out near 0, lower bar
                xp_out_safe = max(xp_out, 0.1)
                passes_threshold = (xp_gain / xp_out_safe) > xp_threshold
            else:
                # Absolute: new - old >= threshold
                passes_threshold = xp_gain >= xp_threshold

            # Also enforce xp_gain >= 2 (minimum gain, from suggest_transfer_in logic)
            if xp_gain < 2:
                print(f"[GW{self.gameweek}] Skipped transfer {transfer_in} → {out} (xp_gain={xp_gain:.1f} < 2)")
                break

            if not passes_threshold:
                pct_improve = (xp_gain / max(xp_out, 0.1)) * 100
                print(f"[GW{self.gameweek}] Skipped transfer {transfer_in} → {out} (xp improvement {pct_improve:.1f}% < {xp_threshold * 100:.0f}% threshold)")
                break

            # Execute transfer
            self.transfer(out, transfer_in, pos)
            if self.squad_size() != SQUAD_SIZE:
                self.remove_excess_players()

            # Update budget tracking
            if use_budget_constraint:
                self.transfer_budget_spent += xp_gain
                transfer_budget_remaining = strategy_config.transfer_budget_per_gw - self.transfer_budget_spent
                print(f"[GW{self.gameweek}] Transferred {transfer_in} for {out}; budget used: {xp_gain:.1f}, remaining: {transfer_budget_remaining:.1f}")

    # ------------------------------------------------------------------
    # Chips
    # ------------------------------------------------------------------

    def any_chip_in_use(self):
        return self.chip_triple_captain_active or self.chip_bench_boost_active or self.chip_free_hit_active

    def auto_chips(self, triple_captain_threshold=8, bench_threshold=4, free_hit_threshold=35, wildcard_threshold=30):
        print('Checking for any chips...', end='\r')
        if self.season == '2022-23' and self.gameweek in (7, 8):
            return

        xi_xp = self.team_xp(include_subs=False)

        if self.chip_triple_captain_available and not self.any_chip_in_use():
            captain_xp = self.player_xp(self.captain, self.player_pos(self.captain))
            if captain_xp > triple_captain_threshold and self.gameweek > 1:
                print(f'CHIP: Triple Captain activated on GW{self.gameweek} for {self.captain} with {captain_xp:.2f} xP\n')
                self.chips_used.append(['Triple Captain', self.gameweek])
                self.chip_triple_captain_available = False
                self.chip_triple_captain_active = True

        if self.chip_bench_boost_available and not self.any_chip_in_use():
            all_xp = self.team_xp(include_subs=True)
            bench_xp = all_xp - xi_xp
            if bench_xp > bench_threshold and self.gameweek > 1:
                print(f'CHIP: Bench Boost activated on GW{self.gameweek} for {bench_xp:.2f} xP\n')
                self.chips_used.append(['Bench Boost', self.gameweek])
                self.chip_bench_boost_available = False
                self.chip_bench_boost_active = True

        if self.chip_free_hit_available and not self.any_chip_in_use():
            if xi_xp < free_hit_threshold:
                self.chip_free_hit_available = False
                self.chip_free_hit_active = True
                self.chips_used.append(['Free Hit', self.gameweek])
                print(f'CHIP: Free Hit activated on GW{self.gameweek} for {xi_xp:.2f} xP\n')
                self.return_subs_to_team()
                self.free_hit_team = [[self.gks, self.defs, self.mids, self.fwds], self.budget, self.gameweek, dict(self.purchase_prices)]
                self.initial_team_generator()

        if self.chip_wildcard_available and not self.any_chip_in_use():
            if xi_xp < wildcard_threshold:
                print(f'CHIP: Wildcard activated on GW{self.gameweek} for {xi_xp:.2f} xP\n')
                self.initial_team_generator()
                print(f'Current Team xP {xi_xp:.2f} vs New xP {self.team_xp(include_subs=True):.2f}')
                self.chip_wildcard_available = False
                self.chips_used.append(['Wildcard', self.gameweek])

    def _load_free_hit_team(self):
        pos_players, budget, gw, saved_prices = self.free_hit_team
        self.return_subs_to_team()
        for pos in POSITIONS:
            self._pos_squad_list(pos).clear()
        self.subs = []

        print(f'Loading pre-Free Hit team from GW{gw}', end='\r')
        for pos, players in zip(POSITIONS, pos_players):
            for player in players:
                self.add_player(player, pos, 0)

        self.budget = budget
        self.purchase_prices = saved_prices
        self.free_hit_team = None
        print(f'Loaded pre-Free Hit team {self.budget:.2f} budget remaining', end='\r')

    # ------------------------------------------------------------------
    # Team building
    # ------------------------------------------------------------------

    def initial_team_generator(self):
        print('Selecting fresh team...')
        if self.gameweek != 1:
            self.budget = self.team_value() + self.budget

        spending_budget = self.budget - sum(
            self.pos_size(pos) * MIN_PRICE[pos] for pos in POSITIONS
        )

        for pos in POSITIONS:
            self._pos_squad_list(pos).clear()
        self.subs = []

        ratio_split = {'GK': 0.1, 'FWD': 0.2, 'MID': 0.4, 'DEF': 0.3}
        fillers = {'GK': 1, 'FWD': 1, 'MID': 2, 'DEF': 2}

        budget_excess = 0
        for pos in ['GK', 'FWD', 'MID', 'DEF']:
            pos_budget = spending_budget * ratio_split[pos] + self.pos_size(pos) * MIN_PRICE[pos]
            _, budget_excess = self._get_best_players(pos, pos_budget + budget_excess, fillers[pos])

        print('Complete!\n')

    def _get_best_players(self, position, budget, fillers):
        players_by_xp = self.all_xp[POSITIONS.index(position)].sort_values(by='xP', ascending=False).Name.tolist()
        needed = self.pos_size(position)
        bought = []
        premium = 0
        budget_fillers = 0
        total_spent = 0
        original_budget = budget

        last_gw_data = self.fpl.get_gw_data(self.season, self.gameweek + 1)
        if last_gw_data.empty:
            last_gw_data = self.gw_data
        for player in players_by_xp:
            if len(bought) >= needed:
                break
            p_cost = self.player_value(player, last_gw_data)
            if p_cost is None:
                continue
            if premium < needed - fillers and p_cost <= budget:
                if self.transfer_in_allowed(player, position, p_cost):
                    self.add_player(player, position, p_cost)
                    bought.append(player)
                    budget -= p_cost
                    premium += 1
                    total_spent += p_cost
            elif budget_fillers < fillers and p_cost <= 6:
                if self.transfer_in_allowed(player, position, p_cost):
                    self.add_player(player, position, p_cost)
                    bought.append(player)
                    budget -= p_cost
                    budget_fillers += 1
                    total_spent += p_cost

        print(f'{len(bought)} players bought for {position}')
        return bought, original_budget - total_spent

    # ------------------------------------------------------------------
    # Squad info / display
    # ------------------------------------------------------------------

    def squad_size(self):
        return sum(len(self._pos_squad_list(pos)) for pos in POSITIONS) + len(self.subs)

    def xi_size(self):
        return sum(len(self._pos_squad_list(pos)) for pos in POSITIONS)

    def team_value(self):
        value = 0
        count = 0
        for name, _ in self._all_squad_players():
            val = self.player_value(name, self.gw_data)
            if val is not None:
                value += val
                count += 1
            elif count > 0:
                value += value / count
        return value

    def display(self):
        for pos in POSITIONS:
            print(f'{pos}: {self._pos_squad_list(pos)}')
        print(f'SUBS: {self.subs}')
        print(f'C: {self.captain}, VC: {self.vice_captain}')
        print(f'Budget: {self.budget:.1f}\n')

    def get_team(self):
        return self.gks, self.defs, self.mids, self.fwds

    def result_summary(self):
        if self.squad_size() != SQUAD_SIZE:
            print('(cannot print results) Team not complete, squad size', self.squad_size())
            return
        if self.season == '2022-23' and self.gameweek == 7:
            return 0
        if self.season == '2023-24' and self.gameweek > self.recent_gw:
            all_p = self.team_xp_list()
            print('IMPORTANT: No actual points available, displaying xP instead\n')
        else:
            all_p = self.team_p_list(include_subs=True) if self.chip_bench_boost_active else self.team_p_list()
        self._list_to_summary(all_p)

    def _list_to_summary(self, p_list):
        all_p = sorted(p_list, key=lambda x: x[2], reverse=True)
        print(
            f'GW{self.gameweek} - {self.season} | P: {self.team_p()} | xP: {self.team_xp():.2f} | '
            f'B: {self.budget:.1f} | C: {self.captain} | VC: {self.vice_captain}\n'
            f'  Top 3: {all_p[0][0]} {all_p[0][1]} {all_p[0][2]}, '
            f'{all_p[1][0]} {all_p[1][1]} {all_p[1][2]}, '
            f'{all_p[2][0]} {all_p[2][1]} {all_p[2][2]}\n'
            f'  Worst 3: {all_p[-1][0]} {all_p[-1][1]} {all_p[-1][2]}, '
            f'{all_p[-2][0]} {all_p[-2][1]} {all_p[-2][2]}, '
            f'{all_p[-3][0]} {all_p[-3][1]} {all_p[-3][2]}\n'
        )

    # ------------------------------------------------------------------
    # Player lookups
    # ------------------------------------------------------------------

    def player_value(self, player, gw_data):
        return self.fpl.get_price(self.gameweek, player, gw_data)

    def selling_price(self, player):
        current = self.player_value(player, self.gw_data)
        if current is None:
            return 0
        bought_at = self.purchase_prices.get(player, current)
        if current > bought_at:
            profit = current - bought_at
            return round(bought_at + int(round(profit * 10)) // 2 / 10, 1)
        return current

    def player_pos(self, player):
        cached = self._pos_cache.get(player)
        if cached is not None:
            return cached
        # Check actual squad slot first — player may have been transferred into a
        # position that differs from gw_data (e.g. position-changed historical player)
        for pos, lst in zip(POSITIONS, [self.gks, self.defs, self.mids, self.fwds]):
            if player in lst:
                self._pos_cache[player] = pos
                return pos
        for sub_name, sub_pos in self.subs:
            if sub_name == player:
                self._pos_cache[player] = sub_pos
                return sub_pos
        pos = (self.positions_list.get(player)
               or self.prev_pos_list.get(player)
               or self.fpl.position_dict(self.gameweek).get(player))
        if pos is not None:
            self._pos_cache[player] = pos
        return pos

    def get_club_counts(self, gw_data):
        counts = {}
        for name, _ in self._all_squad_players():
            club = str(self.fpl.get_player_team(name, self.gameweek, gw_data))
            counts[club] = counts.get(club, 0) + 1
        return counts

    def _counts_from_list(self, player_list):
        counts = {}
        for player in player_list:
            club = self.fpl.get_player_team(player, self.gameweek)
            counts[club] = counts.get(club, 0) + 1
        return counts

    def _generate_player_list(self, position):
        return [name for name, pos in self.player_list.items() if pos == position]

    def get_player_list(self, position):
        return self._pos_player_lists[position]

    def id_to_name(self, id):
        return self.fpl.id_to_name[id]

    def get_avg_score(self):
        return self.fpl.get_avg_score_list()

    def pos_size(self, position):
        return MAX_PER_POS.get(position, 0)

    def pos_price_minimum(self, position):
        return MIN_PRICE.get(position, 4.0)

    # ------------------------------------------------------------------
    # Substitution swaps (players who didn't play)
    # ------------------------------------------------------------------

    def swap_players_who_didnt_play(self):
        players_who_didnt_play = self.fpl.get_players_who_didnt_play(self.gameweek)

        team_nonplayers = [
            p for p, _ in self._all_xi_players()
            if p in players_who_didnt_play
        ]

        if not team_nonplayers:
            return

        # Mutable list kept in sync with self.subs as we process swaps
        sub_list = [s for s in self.subs if s[0] not in team_nonplayers]

        for player in team_nonplayers:
            sub_made = False
            player_pos = self.positions_list.get(player)

            for sub in sub_list:
                if sub[1] == player_pos and sub[0] not in team_nonplayers:
                    self.remove_sub(sub[0], sub[1])
                    if sub in self.subs:
                        self.subs.remove(sub)
                    sub_list.remove(sub)
                    self.add_sub(player, sub[1])
                    self.subs.append([player, sub[1]])
                    sub_made = True
                    break

            if not sub_made:
                for sub in sub_list:
                    if sub[0] not in team_nonplayers and sub[1] != 'GK':
                        self.remove_sub(sub[0], sub[1])
                        if sub in self.subs:
                            self.subs.remove(sub)
                        sub_list.remove(sub)
                        try:
                            self.add_sub(player, self.positions_list[player])
                            self.subs.append([player, self.positions_list[player]])
                        except KeyError:
                            pass
                        break

    def remove_excess_players(self):
        for pos in POSITIONS:
            while len(self._pos_squad_list(pos)) > MAX_PER_POS[pos]:
                candidates = self._pos_squad_list(pos)
                worst = min(candidates, key=lambda p: self.player_p(p, pos))
                self.remove_player(worst, pos)
                print(f'Removed {worst} from {pos}', end='\r')

    # ------------------------------------------------------------------
    # Multi-GW xP discounting
    # ------------------------------------------------------------------

    def _get_n_gws_xp(self, n, discount_factor):
        if self.gameweek < 36:
            return self.fpl.discount_next_n_gws(self.combined_xp, self.gameweek, n, discount_factor=discount_factor)
        return self.combined_xp

    # ------------------------------------------------------------------
    # Compatibility aliases (used by manager.py)
    # ------------------------------------------------------------------

    def get_n_gws_xp(self, n, discount_factor):
        return self._get_n_gws_xp(n, discount_factor)

    def name_in_list(self, name, lst):
        return any(name in player for player in lst)
