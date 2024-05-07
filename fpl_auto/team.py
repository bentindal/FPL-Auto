import pandas as pd
import fpl_auto.data as fpl
import datetime as dt
class team:
    def __init__(self, season, gameweek=1, budget=100.0, transfers_left=0, players=[[], [], [], [], []], chips_used=[], transfer_history=[], triple_captain_available=True, bench_boost_available=True, free_hit_available=True, wildcard_available=True, free_hit_team=None):
        """
        Initializes a team object.

        Parameters:
            - season (str): The season of the team.
            - gameweek (int): The current gameweek.
            - budget (int): The budget for the team (default: 100).
            - gks (list): List of goalkeepers in the team (default: []).
            - defs (list): List of defenders in the team (default: []).
            - mids (list): List of midfielders in the team (default: []).
            - fwds (list): List of forwards in the team (default: []).
            - subs (list): List of substitutes in the team (default: []).

        Returns:
            - None
        """
                
        self.fpl = fpl.fpl_data('data', season)
        self.season = season
        self.gameweek = gameweek
        self.budget = budget
        self.gks = players[0]
        self.defs = players[1]
        self.mids = players[2]
        self.fwds = players[3]
        self.subs = players[4]
        self.free_hit_team = free_hit_team

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

        if self.chip_wildcard_available is False and self.gameweek == 19:
            print('============== Wildcard Returned! ==============\n')
            self.chip_wildcard_available = True
        
        self.positions = ['GK', 'DEF', 'MID', 'FWD']
        self.gk_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/GK.tsv', sep='\t')
        self.def_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/DEF.tsv', sep='\t')
        self.mid_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/MID.tsv', sep='\t')
        self.fwd_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/FWD.tsv', sep='\t')
        self.combined_xp = [self.gk_xp, self.def_xp, self.mid_xp, self.fwd_xp]
        
        self.all_xp = self.get_n_gws_xp(5, discount_factor=0.8)
        
        self.player_list = self.fpl.player_list
        self.gk_player_list = self.generate_player_list('GK')
        self.def_player_list = self.generate_player_list('DEF')
        self.mid_player_list = self.generate_player_list('MID')
        self.fwd_player_list = self.generate_player_list('FWD')

        self.gk_xp_dict = dict(zip(self.gk_xp.Name, self.gk_xp.xP))
        self.def_xp_dict = dict(zip(self.def_xp.Name, self.def_xp.xP))
        self.mid_xp_dict = dict(zip(self.mid_xp.Name, self.mid_xp.xP))
        self.fwd_xp_dict = dict(zip(self.fwd_xp.Name, self.fwd_xp.xP))
        self.player_xp_list = self.gk_xp.xP.tolist() + self.def_xp.xP.tolist() + self.mid_xp.xP.tolist() + self.fwd_xp.xP.tolist()
        
        self.prev_pos_list = self.fpl.position_dict(self.gameweek - 1)

        self.captain = ''
        self.vice_captain = ''

        try:
            self.recent_gw = self.fpl.get_recent_gw() - 1
        except:
            self.recent_gw = 38
        if self.gameweek >= self.recent_gw and self.season == '2023-24':
            self.positions_list = self.fpl.position_dict(self.recent_gw)
            self.points_scored = self.fpl.actual_points_dict(season, self.recent_gw - 1)
        elif self.gameweek == 8 and self.season == '2023-24':
            self.positions_list = self.fpl.position_dict(self.gameweek)
            self.points_scored = self.fpl.actual_points_dict(season, gameweek)
        else:
            self.positions_list = self.fpl.position_dict(self.gameweek - 1)
            self.points_scored = self.fpl.actual_points_dict(season, gameweek - 1)
        
        # Optional stop list for players
        self.player_stop_list = []

        if self.free_hit_team is not None and self.free_hit_team[2] == self.gameweek - 1: 
            self.load_free_hit_team()

    def check_violate_club_rule(self, player, club_counts=None):
        """
        Checks if adding a player would violate the club rule.
        
        Parameters:
            - player (str): The name of the player.
            - club_counts (dict): A dictionary containing the number of players from each club in the team (default: None)."""
        player_club = self.fpl.get_player_team(player, self.gameweek, self.gw_data)
        if club_counts is None:
            club_counts = self.get_club_counts(self.gw_data)
        try:
            if player_club not in club_counts:
                club_counts[player_club] = 0
            club_counts[player_club] += 1
            if club_counts[player_club] > 3:
                return True
        except TypeError:
            return False
        return False
    
    def add_player(self, player, position='none', custom_price=None, force=False):
        """
        Adds a player to the team.

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - None
        """
        force = False
        if self.transfer_in_allowed(player, position, custom_price) or force and self.squad_size() < 15:
            #print('Adding', player, 'to', position)
            if custom_price == None:
                p_cost = self.player_value(player, self.gw_data)
            else:
                p_cost = custom_price

            if position == 'none':
                position = self.player_pos(player)

            position_list = getattr(self, position.lower() + 's')

            position_list.append(player)
            self.budget -= p_cost        

    def transfer_in_allowed(self, player, position='none', custom_price=None):
        """
        Checks if a transfer in is allowed for a player.

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - bool: True if the transfer in is allowed, False otherwise.
        """
        if custom_price == None:
            p_cost = self.player_value(player, self.gw_data)
        else:
            p_cost = custom_price

        if position == 'none':
            position = self.player_pos(player)

        position_list = getattr(self, position.lower() + 's')
        
        if player in self.player_stop_list:
            #print(f'FAILED (player on stoplist) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
            return False
        
        if position not in ['GK', 'DEF', 'MID', 'FWD']:
            #print(f'FAILED (invalid pos {position}) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
            return False
        
        player_club = str(self.fpl.get_player_team(player, self.gameweek, self.gw_data))  # Convert player_club to a string
        club_counts = self.get_club_counts(self.gw_data)
        
        # Add 1 to the count of the player's club
        if player_club not in club_counts:
            club_counts[player_club] = 0

        club_counts[player_club] += 1
        # Check if the count is greater than 3
        if club_counts[player_club] > 3 and player_club != 'None':
            # Cannot add {player}, {player_club} has 3 players already
            #print(f'FAILED (club count > 3) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
            return False

        if p_cost == None:
            #print(f'FAILED (none player value) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
            return False
        
        if player in self.player_list:
            if p_cost != None:
                if len(position_list) < (self.get_max_players(position) + 1):
                    if self.budget >= p_cost:
                        if self.squad_size() < 16:
                            return True
                        else:
                            #print(f'FAILED (squad too big) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
                            return False
                    else:
                        #print(f'FAILED (cannot afford) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')      
                        return False
                else:
                    #print(f'FAILED (too many players in pos already) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
                    return False
            else:
                #print(f'FAILED (cost is none) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
                return False
        else:
            #print(f'FAILED (not on player list?) {player} to {position} for {p_cost}, Budget {self.budget} {self.squad_size()} players in squad')
            return False

    def get_max_players(self, position):
        """
        Returns the maximum number of players allowed for a given position.

        Parameters:
            - position (str): The position ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - int: The maximum number of players allowed for the given position.
        """
        if position == 'GK':
            return 2
        elif position == 'DEF':
            return 5
        elif position == 'MID':
            return 5
        elif position == 'FWD':
            return 3
    
    def generate_player_list(self, position):
        """
        Generates a list of players for a given position.

        Parameters:
            - position (str): The position ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - list: A list of players for the given position.
        """
        player_to_pos = self.player_list
        player_list = []
        for player in player_to_pos:
            if player_to_pos[player] == position:
                player_list.append(player)
        return player_list
    
    def get_player_list(self, position):
        """
        Returns the list of players for a given position.

        Parameters:
            - position (str): The position ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - list: A list of players for the given position.
        """
        if position == 'GK':
            return self.gk_player_list
        elif position == 'DEF':
            return self.def_player_list
        elif position == 'MID':
            return self.mid_player_list
        elif position == 'FWD':
            return self.fwd_player_list
        
    def remove_player(self, player, position):
        """
        Removes a player from the team.

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - None
        """
        self.return_subs_to_team()
        if position == 'GK':
            self.gks.remove(player)
            self.budget += self.player_value(player, self.gw_data)
        elif position == 'DEF':
            self.defs.remove(player)
            self.budget += self.player_value(player, self.gw_data)
        elif position == 'MID':
            self.mids.remove(player)
            self.budget += self.player_value(player, self.gw_data)
        elif position == 'FWD':
            self.fwds.remove(player)
            self.budget += self.player_value(player, self.gw_data)
        else:
            print('Invalid position')

        #print(f'Removed {player} from {position}, {self.squad_size()} players in squad')
    def add_sub(self, player, position):
        """
        Removes a player from the team without affecting the budget

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').
        """
        try:
            if position == 'GK':
                self.gks.remove(player)
            elif position == 'DEF':
                self.defs.remove(player)
            elif position == 'MID':
                self.mids.remove(player)
            elif position == 'FWD':
                self.fwds.remove(player)
            else:
                print('Invalid position, cannot sub player')
        except ValueError:
            pass

    def remove_sub(self, player, position):
        """
        Removes a substitute player from the team.

        Parameters:
        - player (str): The name of the player.
        - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').
        """
        if position == 'GK':
            self.gks.append(player)
        elif position == 'DEF':
            self.defs.append(player)
        elif position == 'MID':
            self.mids.append(player)
        elif position == 'FWD':
            self.fwds.append(player)
        else:
            print('Invalid position, cannot add sub')
            
    def display(self):
        """
        Displays the current team lineup.
        """
        print(f'GK: {self.gks}')
        print(f'DEF: {self.defs}')
        print(f'MID: {self.mids}')
        print(f'FWD: {self.fwds}')
        print(f'SUBS: {self.subs}')
        print(f'C: {self.captain}, VC: {self.vice_captain}')
        print(f'Budget: {self.budget:.1f}\n')

    def get_team(self):
        """
        Returns the current team lineup.

        Returns:
            - tuple: A tuple containing the lists of goalkeepers, defenders, midfielders, and forwards in the team.
        """
        return self.gks, self.defs, self.mids, self.fwds
    
    def get_gks(self):
        """
        Returns the list of goalkeepers in the team.

        Returns:
            - list: The list of goalkeepers in the team.
        """
        return self.gks
    
    def get_defs(self):
        """
        Returns the list of defenders in the team.

        Returns:
            - list: The list of defenders in the team.
        """
        return self.defs
    
    def get_mids(self):
        """
        Returns the list of midfielders in the team.

        Returns:
            - list: The list of midfielders in the team.
        """
        return self.mids
    
    def get_fwds(self):
        """
        Returns the list of forwards in the team.

        Returns:
            - list: The list of forwards in the team.
        """
        return self.fwds
    
    def get_subs(self):
        """
        Returns the list of substitutes in the team.

        Returns:
            - list: The list of substitutes in the team.
        """
        return self.subs
    
    def return_subs_to_team(self):
        """
        Returns the substitutes to the team.

        Returns:
            - None
        """
        for sub in self.subs:
            self.return_player_to_team(sub[0], sub[1])
        self.subs = []

    def return_player_to_team(self, player, position):
        """
        Returns a player from the substitutes to the team.

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - None
        """
        if position == 'GK':
            self.gks.append(player)
        elif position == 'DEF':
            self.defs.append(player)
        elif position == 'MID':
            self.mids.append(player)
        elif position == 'FWD':
            self.fwds.append(player)
        else:
            print('Invalid position, cannot return player to team')

    def suggest_subs(self):
        """
        Suggests the substitutions to be made in the team.

        Returns:
            - list: A list of suggested substitutions, each containing the name of the player and their position.
        """
        if self.squad_size() != 15:
            print(f'Error: Squad has not been filled up (Size {self.squad_size()})')
            self.remove_excess_players()
        # Rank each player by their xP, list the lowest xP first
        ranked_gk = []

        # Return subs to team
        self.return_subs_to_team()
        # Sort players by xP
        for player in self.gks:
            if player in self.gk_xp_dict:
                ranked_gk.append([player, self.gk_xp_dict[player], 'GK'])
            else:
                ranked_gk.append([player, 0, 'GK'])
        ranked_gk.sort(key=lambda x: float(x[1]))
        ranked_others = []
        for player in self.defs:
            if player in self.def_xp_dict:
                ranked_others.append([player, self.def_xp_dict[player], 'DEF'])
            else:
                ranked_others.append([player, 0, 'DEF'])
        for player in self.mids:
            if player in self.mid_xp_dict:
                ranked_others.append([player, self.mid_xp_dict[player], 'MID'])
            else:
                ranked_others.append([player, 0, 'MID'])
        for player in self.fwds:
            if player in self.fwd_xp_dict:
                ranked_others.append([player, self.fwd_xp_dict[player], 'FWD'])
            else:
                ranked_others.append([player, 0, 'FWD'])
                
        ranked_others.sort(key=lambda x: float(x[1]))
          
        # Suggest subs
        subs = []
        subs.append([ranked_gk[0][0], 'GK'])
        
        # Limit substitution of maximum two players of the same position (except GK)
        positions_substituted = {'GK': 1}
        for player in ranked_others:
            if positions_substituted.get(player[2], 0) < 2 and len(subs) < 4:
                subs.append([player[0], player[2]])
                positions_substituted[player[2]] = positions_substituted.get(player[2], 0) + 1
        
        return subs

    def make_subs(self, subs):
        """
        Makes the substitutions in the team.

        Parameters:
            - subs (list): A list of substitutions, each containing the name of the player and their position.

        Returns:
            - None
        """
        # Add subs to list
        self.subs = subs
        # Remove players from team
        for sub in subs:
            self.add_sub(sub[0], sub[1])
    
    def auto_subs(self):
        """
        Automatically makes substitutions in the team.

        Returns:
            - None
        """
        self.return_subs_to_team()
        suggested_subs = self.suggest_subs()
        self.make_subs(suggested_subs)

    def player_xp(self, player, position):
        """
        Returns the expected points (xP) for a player in a given position.

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - float: The expected points for the player.
        """
        if position == None:
            position = self.player_pos(player)

        xp_dict = self.all_xp[self.pos_to_num(position)]
        xp_dict = dict(zip(xp_dict.Name, xp_dict.xP))
        
        # return xP for player
        if player in xp_dict:
            return xp_dict[player]
        else:
            #print(f'No xP found for player {player} {position}')
            return 0
        
    def get_all_xp(self, include_subs=False):
        """
        Returns the expected points (xP) for all players in the team.

        Parameters:
            - include_subs (bool): Whether to include the expected points for substitutes (default: False).

        Returns:
            - list: A list of player names and their expected points.
        """
        # List of players and their xP
        team_xp = []
        # Get xP for each player in team
        for player in self.gks:
            if player == self.captain:
                team_xp.append([player, self.player_xp(player, 'GK') * 2])
            else:
                team_xp.append([player, self.player_xp(player, 'GK')])
        for player in self.defs:
            if player == self.captain:
                team_xp.append([player, self.player_xp(player, 'DEF') * 2])
            else:
                team_xp.append([player, self.player_xp(player, 'DEF')])
        for player in self.mids:
            if player == self.captain:
                team_xp.append([player, self.player_xp(player, 'MID') * 2])
            else:
                team_xp.append([player, self.player_xp(player, 'MID')])
        for player in self.fwds:
            if player == self.captain:
                team_xp.append([player, self.player_xp(player, 'FWD') * 2])
            else:
                team_xp.append([player, self.player_xp(player, 'FWD')])
                
        if include_subs:
            for player in self.subs:
                team_xp.append([player[0], self.player_xp(player[0], player[1])])
        
        return team_xp
    
    def get_all_p(self, include_subs=False):
        """
        Returns the expected points (p) for all players in the team.

        Parameters:
            - include_subs (bool): Whether to include the expected points for substitutes (default: False).

        Returns:
            - list: A list of player names and their expected points.
        """
        # List of players and their p
        team_p = []
        # Get p for each player in team
        for player in self.gks:
            if player == self.captain and self.chip_triple_captain_active:
                team_p.append([player, self.player_p(player, 'GK') * 3])
            elif player == self.captain:
                team_p.append([player, self.player_p(player, 'GK') * 2])
            else:
                team_p.append([player, self.player_p(player, 'GK')])
        for player in self.defs:
            if player == self.captain and self.chip_triple_captain_active:
                team_p.append([player, self.player_p(player, 'DEF') * 3])
            elif player == self.captain:
                team_p.append([player, self.player_p(player, 'DEF') * 2])
            else:
                team_p.append([player, self.player_p(player, 'DEF')])
        for player in self.mids:
            if player == self.captain and self.chip_triple_captain_active:
                team_p.append([player, self.player_p(player, 'MID') * 3])
            elif player == self.captain:
                team_p.append([player, self.player_p(player, 'MID') * 2])
            else:
                team_p.append([player, self.player_p(player, 'MID')])
        for player in self.fwds:
            if player == self.captain and self.chip_triple_captain_active:
                team_p.append([player, self.player_p(player, 'FWD') * 3])
            elif player == self.captain:
                team_p.append([player, self.player_p(player, 'FWD') * 2])
            else:
                team_p.append([player, self.player_p(player, 'FWD')])
                
        if include_subs:
            for player in self.subs:
                team_p.append([player[0], self.player_p(player[0], player[1])])

        return team_p
    
    def squad_size(self):
        """
        Returns the size of the team squad.

        Returns:
            - int: The size of the team squad.
        """
        return len(self.gks) + len(self.defs) + len(self.mids) + len(self.fwds) + len(self.subs)
    
    def xi_size(self):
        return len(self.gks) + len(self.defs) + len(self.mids) + len(self.fwds)
    
    def team_xp(self, include_subs=False):
        """
        Calculates the expected points (xP) for the entire team.

        Returns:
            - float: The total expected points for the team.
        """
        if self.season == '2022-23' and self.gameweek == 7:
            return 0
        
        self.return_subs_to_team()
        self.auto_subs()
        self.auto_captain()
        
        # Get xP for each player in team
        if include_subs:
            xp_list = self.get_all_xp(include_subs=True)
        else:
            xp_list = self.get_all_xp()
        
        total_xp = 0
        if self.squad_size() != 15:
           print(f'Team not complete, squad size {self.squad_size()}')
           self.return_subs_to_team()
           self.display()
           self.remove_excess_players()
           self.display()
        else:
            for player in xp_list:
                if player[0] == self.captain:
                    total_xp += player[1] * 2
                else:
                    total_xp += player[1]

        return total_xp
    
    def remove_excess_players(self):
        """
        Removes excess players from the team.

        Returns:
            - None
        """
        # Find the position that has an excess player
        for position in self.positions:
            if len(getattr(self, position.lower() + 's')) > self.get_max_players(position):
                # Find the player with the lowest xP in that position
                min_xp = 100
                min_player = ''
                for player in getattr(self, position.lower() + 's'):
                    if self.player_xp(player, position) < min_xp:
                        min_xp = self.player_p(player, position)
                        min_player = player
                # Remove the player
                self.remove_player(min_player, position)
                print(f'Removed {min_player} from {position}', end='\r')
            
    def player_p(self, player, position):
        """
        Returns the actual points scored by a player in a given position.

        Parameters:
            - player (str): The name of the player.
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - int: The actual points scored by the player.
        """
        if player in self.points_scored:
            captain_played = self.captain_played()
            # Captain played and triple active
            if self.captain == player and captain_played and self.chip_triple_captain_active:
                return self.points_scored[player] * 3
            # Captain played
            elif self.captain == player and captain_played:
                return self.points_scored[player] * 2
            # Captain did not play but vice
            elif self.vice_captain == player and not captain_played:
                return self.points_scored[player] * 2
            # not Captain Played but vice and triple captain
            elif self.vice_captain == player and not captain_played and self.chip_triple_captain_active:
                return self.points_scored[player] * 3
            # regular player
            else:
                return self.points_scored[player]
        else:
            #print(f'Player {player} {position} points not found for GW{self.gameweek} {self.season}!')
            return 0
    
    def captain_played(self):
        """
        Checks if the captain has played in the current gameweek.

        Returns:
            - bool: True if the captain has played, False otherwise.
        """
        # Captain and Vice-Captain points
        try:
            captain_p = self.player_p(self.captain, self.player_pos(self.captain))
            if captain_p != 0:
                return True
        except:
            pass

        return False
        
    def team_p(self, include_subs=False):
        """
        Calculates the actual points scored by the team.

        Returns:
            - int: The total actual points scored by the team.
        """
        if self.season == '2022-23' and self.gameweek == 7:
            return 0
        if self.season == '2023-24' and self.gameweek > self.recent_gw:
            return 0
        
        self.return_subs_to_team()
        
        self.auto_subs()
        
        self.auto_captain()
        
        self.swap_players_who_didnt_play()

        all_p = 0

        for player in self.gks:
            all_p += self.player_p(player, 'GK')
        for player in self.defs:
            all_p += self.player_p(player, 'DEF')
        for player in self.mids:
            all_p += self.player_p(player, 'MID')
        for player in self.fwds:
            all_p += self.player_p(player, 'FWD')
        if include_subs:
            for player in self.subs:
                all_p += self.player_p(player, self.player_pos(player))

        if self.chip_bench_boost_active:
            for player in self.subs:
                all_p += self.player_p(player[0], player[1])

        return all_p
    
    def team_p_list(self, include_subs=False):
        """
        Returns a list of points scored by each player in the team (Name, Position, Points).

        Parameters:
            - include_subs (bool): Whether to include the points scored by substitutes (default: False).

        Returns:
            - list: A list of points scored by each player in the team.
        """
        p_list = []
        captain_played = self.captain_played()
        for player in self.gks:
            if player == self.captain and captain_played:
                p_list.append([f'(C) {player}', 'GK', self.player_p(player, 'GK')])
            elif player == self.vice_captain and not captain_played:
                p_list.append([f'(VC) {player}', 'GK', self.player_p(player, 'GK')])
            else:
                p_list.append([player, 'GK', self.player_p(player, 'GK')])
        for player in self.defs:
            if player == self.captain and captain_played:
                p_list.append([f'(C) {player}', 'DEF', self.player_p(player, 'DEF')])
            elif player == self.vice_captain and not captain_played:
                p_list.append([f'(VC) {player}', 'DEF', self.player_p(player, 'DEF')])
            else:
                p_list.append([player, 'DEF', self.player_p(player, 'DEF')])
        for player in self.mids:
            if player == self.captain and captain_played:
                p_list.append([f'(C) {player}', 'MID', self.player_p(player, 'MID')])
            elif player == self.vice_captain and not captain_played:
                p_list.append([f'(VC) {player}', 'MID', self.player_p(player, 'MID')])
            else:
                p_list.append([player, 'MID', self.player_p(player, 'MID')])
        for player in self.fwds:
            if player == self.captain and captain_played:
                p_list.append([f'(C) {player}', 'FWD', self.player_p(player, 'FWD')])
            elif player == self.vice_captain and not captain_played:
                p_list.append([f'(VC) {player}', 'FWD', self.player_p(player, 'FWD')])
            else:
                p_list.append([player, 'FWD', self.player_p(player, 'FWD')])
        if include_subs:
            for player in self.subs:
                p_list.append([player[0], player[1], self.player_p(player[0], player[1])])

        return p_list
    
    def team_xp_list(self):
        """
        Returns a list of points scored by each player in the team (Name, Position, Points).

        Returns:
            - list: A list of points scored by each player in the team.
        """
        xp_list = []
        self.auto_subs()
        for player in self.gks:
            if player == self.captain:
                xp_list.append([f'(C) {player}', 'GK', self.player_xp(player, 'GK') * 2])
            else:
                xp_list.append([player, 'GK', self.player_xp(player, 'GK')])
        for player in self.defs:
            if player == self.captain:
                xp_list.append([f'(C) {player}', 'DEF', self.player_xp(player, 'DEF') * 2])
            else:
                xp_list.append([player, 'DEF', self.player_xp(player, 'DEF')])
        for player in self.mids:
            if player == self.captain:
                xp_list.append([f'(C) {player}', 'MID', self.player_xp(player, 'MID') * 2])
            else:
                xp_list.append([player, 'MID', self.player_xp(player, 'MID')])
        for player in self.fwds:
            if player == self.captain:
                xp_list.append([f'(C) {player}', 'FWD', self.player_xp(player, 'FWD') * 2])
            else:
                xp_list.append([player, 'FWD', self.player_xp(player, 'FWD')])

        return xp_list
    
    def p_list(self):
        """
        Returns a list of points scored by each player in the team.

        Returns:
        - list: A list of points scored by each player in the team.
        """
        entire_list = self.team_p_list()
        points_list = [item[2] for item in entire_list]

        return points_list
    
    def player_value(self, player, gw_data):
        """
        Returns the price of a player.

        Parameters:
            - player (str): The name of the player.

        Returns:
            - int: The price of the player.
        """
        value = self.fpl.get_price(self.gameweek, player, gw_data)
        return value
        
    
    def player_pos(self, player):
        """
        Returns the position of a player.

        Parameters:
            - player (str): The name of the player.

        Returns:
            - str: The position of the player.
        """
        # Get position for player
        if player in self.positions_list:
            return self.positions_list[player]
        elif player in self.prev_pos_list:
            return self.prev_pos_list[player]
        next_pos_list = self.fpl.position_dict(self.gameweek)
        if player in next_pos_list:
            return next_pos_list[player]
    
    def suggest_captaincy(self):
        """
        Suggests the captain and vice-captain for the team.

        Returns:
            - None
        """
        # Get xP for each player in team
        xp_list = self.get_all_xp()
        # Sort by xP
        xp_list.sort(key=lambda x: float(x[1]), reverse=True)
        # Suggest captain & Co-captain
        return xp_list[0], xp_list[1]
    
    def update_captain(self, captain, vice_captain):
        """
        Updates the captain and vice-captain for the team.
        
        Parameters:
            - captain (str): The name of the captain.
            - vice_captain (str): The name of the vice-captain.
        """
        self.captain = captain
        self.vice_captain = vice_captain
    
    def auto_captain(self):
        """
        Automatically selects the captain and vice-captain for the team.
        """
        captain, vice_captain = self.suggest_captaincy()
        self.update_captain(captain[0], vice_captain[0])
    
    def suggest_transfer_out(self):
        """
        Suggests a player to transfer out of the team.

        Returns:
            - str: The name of the player to transfer out.
            - str: The position of the player to transfer out.
            - int: The price of the player to transfer out.
        """
        # Get xP for each player in team
        xp_list = self.get_all_xp(include_subs=True)
        # Sort by xP
        xp_list.sort(key=lambda x: float(x[1]), reverse=False)

        for potential_player in xp_list:
            target_name = potential_player[0]
            target_pos = self.player_pos(target_name)
            target_budget = self.fpl.get_price(self.gameweek, target_name, self.gw_data)
            if target_pos != None and target_budget != None and target_budget != None:
                return target_name, target_pos, target_budget
            
        print('No player found to transfer out')
        return '', '', 0
    
    def suggest_transfer_in(self, position, out_player, budget):
        """
        Suggests a player to transfer in for a given position.
        
        Parameters:
            - position (str): The position of the player to transfer in.
            - out_player (str): The name of the player to transfer out.
            - budget (int): The budget available for the transfer.

        Returns:
            - str: The name of the player to transfer in.
        """
        player_xp_list = self.all_xp[self.pos_to_num(position)]
        
        # sort the pandas dataframe by xp
        player_xp_list = player_xp_list.sort_values(by='xP', ascending=False)
        player_xp_list = player_xp_list.values.tolist()
        
        # Remove all players with xP less than 3
        player_xp_list = [player for player in player_xp_list if player[1] >= 3]
        out_xp = self.player_xp(out_player, position)

        for player in player_xp_list:
            p_cost = self.player_value(player[0], self.gw_data)
            p_xp = player[1]
            xp_gain = p_xp - out_xp
            
            if xp_gain < 2 or p_cost is None or self.player_in_squad(player):
                continue

            #print(f'Considering - {player[0]} {position}, xP Gain: {xp_gain}, Budget - Cost: {budget - p_cost}, Player in squad: {self.player_in_squad(player)}, Violate club rule: {self.check_violate_club_rule(player[0])}')

            if player == out_player:
                #print(f'Player {player[0]} is the same as the player being transferred out')
                continue

            if xp_gain >= 2 and p_cost is not None and p_cost <= budget and not self.player_in_squad(player) and not self.check_violate_club_rule(player[0]):
                #print(f'Allowed? {self.transfer_in_allowed(player[0])} for Player {player}')
                if self.transfer_in_allowed(player[0]):
                    return player[0]
                
        return 'No player found to transfer in'
    
    def player_in_squad(self, player):
        """
        Checks if a player is already in the team.

        Parameters:
            - player (str): The name of the player.

        Returns:
            - bool: True if the player is in the team, False otherwise.
        """
        if player[0] in self.gks:
            return True
        elif player[0] in self.defs:
            return True
        elif player[0] in self.mids:
            return True
        elif player[0] in self.fwds:
            return True
        else:
            return False
        
    def transfer(self, transfer_out, transfer_in, position, threshold=4):
        """
        Makes a transfer in the team, as long as it improves the expected points (xP) by at least the threshold.

        Parameters:
            - transfer_out (str): The name of the player to transfer out.
            - transfer_in (str): The name of the player to transfer in.
            - position (str): The position of the players ('GK', 'DEF', 'MID', 'FWD').
            - threshold (int): The minimum improvement in xP required for the transfer (default: 4).
        """
        try:
            out_xp = self.player_xp(transfer_out, position)
            in_xp = self.player_xp(transfer_in, position)
            xp_gain = in_xp - out_xp
            
            if xp_gain >= threshold:
                self.return_subs_to_team()
                
                self.add_player(transfer_in, position)
                self.remove_player(transfer_out, position)
                
                if self.squad_size() == 14:
                    self.add_player(transfer_out, position, force=True)
                elif self.squad_size() == 16:
                    self.remove_player(transfer_in, position)
                else:
                    print(f'TRANSFER: OUT {transfer_out} {position} --> IN {transfer_in} {position} | xP Gain: {xp_gain:.2f}\n')
                    self.transfers_left -= 1
                    self.transfer_history.append([self.gameweek, [transfer_out, transfer_in], round(xp_gain, 2)])
        except ValueError:
            pass
        
    def auto_transfer(self, threshold=4):
        """
        Automatically makes transfers in the team.

        Returns:
            - None
        """
        print('Checking for any transfers...' , end='\r')
        if self.season == '2022-23' and self.gameweek == 7:
            return
        if self.season == '2023-24' and self.gameweek > self.recent_gw:
            return
        if self.gameweek > 35:
            return
        
        if self.transfers_left > 0:
            min_improvement = threshold
            out, pos, budget = self.suggest_transfer_out()

            if pos == '':
                return
            
            if budget + self.budget < self.pos_price_minimum(pos):
                return
            
            transfer_in = self.suggest_transfer_in(pos, out, self.budget + budget)
            if transfer_in != None and self.player_xp(transfer_in, pos) - self.player_xp(out, pos) >= min_improvement:
                self.transfer(out, transfer_in, pos)
                if self.squad_size() != 15:
                    self.remove_excess_players()
                
                # If theres still another transfer left, go again
                if self.transfers_left > 0:
                    out, pos, budget = self.suggest_transfer_out()
                    if pos == '':
                        return
                    
                    if budget + self.budget < self.pos_price_minimum(pos):
                        return
                    
                    transfer_in = self.suggest_transfer_in(pos, out, self.budget + budget)
                    if transfer_in != None and self.player_xp(transfer_in, pos) - self.player_xp(out, pos) >= min_improvement:
                        self.transfer(out, transfer_in, pos)
                        
                        if self.squad_size() != 15:
                            self.remove_excess_players()
            #else:
            #    print(f'No valid transfer found for {out} {pos} xP {self.player_xp(out, pos)} {budget} + {self.budget} = {self.budget + budget}')
                

    def swap_players_who_didnt_play(self):
        """
        Swaps players who didn't play with substitutes in the team.
        """
        # Get players who didn't play
        players_who_didnt_play = self.fpl.get_players_who_didnt_play(self.gameweek)

        # Get a list of players on the team who didnt play
        gks_who_didnt_play = []
        defs_who_didnt_play = []
        mids_who_didnt_play = []
        fwds_who_didnt_play = []
        subs_who_didnt_play = []
        
        # get list of subs names
        sub_list = []
        for sub in self.subs:
            sub_list.append(sub[0])

        for player in players_who_didnt_play:
            if player in self.gks:
                gks_who_didnt_play.append(player)
            elif player in self.defs:
                defs_who_didnt_play.append(player)
            elif player in self.mids:
                mids_who_didnt_play.append(player)
            elif player in self.fwds:
                fwds_who_didnt_play.append(player)
            elif player in sub_list:
                subs_who_didnt_play.append(player)
        
        # Get a list of players on the team who did play
        team_nonplayers = gks_who_didnt_play + defs_who_didnt_play + mids_who_didnt_play + fwds_who_didnt_play
        
        if len(team_nonplayers) > 0:
            sub_list = self.subs
            
            for p in sub_list:
                if p in team_nonplayers:
                    sub_list.remove(p)
            
            #print(f'Players who didnt play: {team_nonplayers}')
            #print(f'Potential subs: {sub_list}')
            
            for player in team_nonplayers:
                
                for sub in sub_list:
                    sub_made = False
                    # Lets try and swap the sub with a player that didnt play
                    
                    # If sub matches play pos and player is not in team
                    if self.player_pos(player) == sub[1] and sub[0] not in team_nonplayers:
                        
                        # Add sub to team
                        self.remove_sub(sub[0], sub[1])
                        # Remove sub from subs
                        self.subs.remove(sub)
                        # Remove player from team
                        self.add_sub(player, sub[1])
                        # Add player to subs
                        self.subs.append([player, sub[1]])
                        #print(f'Swapped {sub[0]} {self.player_p(sub[0], sub[1])} with {player} {self.player_p(player, self.positions_list[player])} (pos match)')
                        
                        sub_made = True
                        break  

                if not sub_made:
                    #print(f'Could not find a pos match for {player} with any sub')
                    # Attempt to swap player with the first sub who plays thats not a gk
                    for sub in sub_list:
                        if sub[0] not in team_nonplayers and sub[1] != 'GK':
                            # Add sub to team
                            self.remove_sub(sub[0], sub[1])
                            # Remove sub from subs
                            self.subs.remove(sub)
                            # Remove player from team
                            try:
                                self.add_sub(player, self.positions_list[player])
                                # Add player to subs
                                self.subs.append([player, self.positions_list[player]])
                                #print(f'Swapped {sub[0]} with {player} (no pos match)')
                                sub_made = True
                            except KeyError:
                                sub_made = False
                            break
                            
    def select_ideal_team(self, fwd_n, fwd_budget, mid_n, mid_budget, def_n, def_budget, gk_n, gk_budget):
        """
        Selects the ideal team based on the budget allocation.

        Parameters:
            - fwd_n (int): The number of forwards to select.
            - fwd_budget (int): The budget allocated for forwards.
            - mid_n (int): The number of midfielders to select.
            - mid_budget (int): The budget allocated for midfielders.
            - def_n (int): The number of defenders to select.
            - def_budget (int): The budget allocated for defenders.
            - gk_n (int): The number of goalkeepers to select.
            - gk_budget (int): The budget allocated for goalkeepers.

        Returns:
            - team: The ideal team.
        """
        temp_t = team(self.season, self.gameweek, self.budget, self.transfers_left, self.gks, self.defs, self.mids, self.fwds)
        counts = {}
        new_fwds = self.initial_players('FWD', fwd_n, fwd_budget, counts)
        all_players = new_fwds
        counts = self.counts_from_list(all_players)
        new_mids = self.initial_players('MID', mid_n, mid_budget, counts)
        all_players = all_players + new_mids
        counts = self.counts_from_list(all_players)
        new_defs = self.initial_players('DEF', def_n, def_budget, counts)
        all_players = all_players + new_defs
        counts = self.counts_from_list(all_players)
        new_gks = self.initial_players('GK', gk_n, gk_budget, counts)

        player_positions = {'GK': (self.gks, new_gks), 'DEF': (self.defs, new_defs), 'MID': (self.mids, new_mids), 'FWD': (self.fwds, new_fwds)}
        
        for position, (_, new_players) in player_positions.items():

            for player in new_players:
                temp_t.add_player(player, position)

        squad_size = temp_t.squad_size()

        if squad_size != 15 or temp_t.budget < 0: 
            print(f'Error: Could not select ideal team (Got: {squad_size}, Required: 15) or budget allocation failed (Budget Remaining: {temp_t.budget}), try changing the budget allocation.')
            return None
        
        return temp_t

    def result_summary(self):
        """
        Displays the result summary for the team based on actual points.
        Best 3 performing players followed by worst 3 performing players.
        If a player is a captain it displays this.
        
        Returns:
        - None
        """
        if self.squad_size() != 15:
            print('(cannot print results) Team not complete, squad size', self.squad_size())
            return

        if self.season == '2022-23' and self.gameweek == 7:
            return 0
        if self.season == '2023-24' and self.gameweek > self.recent_gw:
            all_p = self.team_xp_list()
            print('IMPORTANT: No actual points available, displaying xP instead\n')
        else:
            # Get P for each player in team
            if self.chip_bench_boost_active:
                all_p = self.team_p_list(include_subs=True)
            else:
                all_p = self.team_p_list()

        self.list_to_summary(all_p)
    
    def list_to_summary(self, p_list):
        """
        Displays the result summary for the team based on a list of points scored by each player.

        Parameters:
            - p_list (list): A list of points scored by each player in the team.

        Returns:
            - None
        """
        # Sort by P all_p[x][2]
        all_p = sorted(p_list, key=lambda x: x[2], reverse=True)
        # Display best 3 players
        print(f'''GW{self.gameweek} - {self.season} | P: {self.team_p()} | xP: {self.team_xp():.2f} | B: {self.budget:.1f} | C: {self.captain} | VC: {self.vice_captain}
    Top 3: {all_p[0][0]} {all_p[0][1]} {all_p[0][2]}, {all_p[1][0]} {all_p[1][1]} {all_p[1][2]}, {all_p[2][0]} {all_p[2][1]} {all_p[2][2]}
    Worst 3: {all_p[-1][0]} {all_p[-1][1]} {all_p[-1][2]}, {all_p[-2][0]} {all_p[-2][1]} {all_p[-2][2]}, {all_p[-3][0]} {all_p[-3][1]} {all_p[-3][2]}\n''')

    def name_in_list(self, name, list):
        """
        Checks if a name is in a list (of names).
        """
        for player in list:
            if name in player:
                return True
        return False
    
    def pos_size(self, position):
        """
        Returns the number of players required for a given position.

        Parameters:
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - int: The number of players required for the position.
        """
        if position == 'FWD': 
            return 3
        elif position == 'MID' or position == 'DEF':
            return 5
        elif position == 'GK':
            return 2
        else:
            print(f'Invalid position: {position}')
            return 0

    def initial_team_generator(self):
        """
        Generates a fresh team from scratch that attempts to maximise xP.

        Returns:
            - None
        """
        print('Selecting fresh team...')
        if self.gameweek == 1:
            self.budget = 100
        else:
            self.budget = self.team_value() + self.budget

        spending_budget = self.budget
        
        fwd_min = 3 * self.pos_price_minimum('FWD')
        mid_min = 5 * self.pos_price_minimum('MID')
        def_min = 5 * self.pos_price_minimum('DEF')
        gk_min = 2 * self.pos_price_minimum('GK')

        spending_budget -= fwd_min
        spending_budget -= mid_min
        spending_budget -= def_min
        spending_budget -= gk_min

        self.fwds = []
        self.mids = []
        self.defs = []
        self.gks = []
        self.subs = []
        
        # Work out maximum I can spend
        # FWD, MID, DEF, GK
        ratio_split = [0.2, 0.4, 0.3, 0.1]
        budget_p = [1, 2, 2, 1]

        gk_budget = spending_budget * ratio_split[3] + gk_min
        _, budget_excess = self.get_best_players('GK', gk_budget, budget_p[3])

        fwd_budget = spending_budget * ratio_split[0] + fwd_min
        _, budget_excess = self.get_best_players('FWD', fwd_budget + budget_excess, budget_p[0])

        mid_budget = spending_budget * ratio_split[1] + mid_min
        _, budget_excess = self.get_best_players('MID', mid_budget + budget_excess, budget_p[1])

        def_budget = spending_budget * ratio_split[2] + def_min
        _, budget_excess = self.get_best_players('DEF', def_budget + budget_excess, budget_p[2])
        
        print('Complete!\n')

    def get_best_players(self, position, budget, fillers):
        """
        Selects the best players for a given position based on the budget and number of fillers.

        Parameters:
            - position (str): The position of the players ('GK', 'DEF', 'MID', 'FWD').
            - budget (int): The budget available for the players.
            - fillers (int): The number of fillers to select.

        Returns:
            - list: The list of players selected for the position.
            - int: The budget remaining after selecting the players.
        """
        players_by_xp = self.all_xp[self.pos_to_num(position)].sort_values(by='xP', ascending=False)
        players_by_xp = players_by_xp.Name.tolist()
        players_needed = self.pos_size(position)
        players_bought = []
        premium_players = 0
        budget_players = 0
        total_spent = 0
        original_budget = budget

        last_gw_data = self.fpl.get_gw_data(self.season, self.gameweek + 1)
        for player in players_by_xp:
            p_cost = self.player_value(player, last_gw_data) # <-----! Erroneous line
            
            # If we have enough players, stop
            if len(players_bought) < players_needed and p_cost != None:
                if premium_players < players_needed - fillers and p_cost <= budget:
                    if self.transfer_in_allowed(player, position, p_cost):
                        self.add_player(player, position, p_cost)
                        players_bought.append(player)
                        budget -= p_cost
                        premium_players += 1
                        total_spent += p_cost
                elif budget_players < fillers and p_cost <= 6 and budget_players < fillers:
                    if self.transfer_in_allowed(player, position, p_cost):
                        self.add_player(player, position, p_cost)
                        players_bought.append(player)
                        budget -= p_cost
                        budget_players += 1
                        total_spent += p_cost
        print(f'{len(players_bought)} players bought for {position}')
        budget_remaining = original_budget - total_spent
        return players_bought, budget_remaining

    def pos_to_num(self, position):
        """
        Converts a position to a number.

        Parameters:
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').
        
        Returns:
            - int: The number corresponding to the position.
        """
        if position == 'FWD':
            return 3
        elif position == 'MID':
            return 2
        elif position == 'DEF':
            return 1
        elif position == 'GK':
            return 0
        
    def id_to_name(self, id):
        """
        Converts a player ID to a player name.

        Parameters:
            - id (int): The ID of the player.
        
        Returns:
            - str: The name of the player.
        """
        return self.fpl.id_to_name[id]
    
    def get_avg_score(self):
        """
        Returns the average score of the team.

        Returns:
            - float: The average score of the team.
        """
        return self.fpl.get_avg_score_list()
    
    def get_club_counts(self, gw_data):
        """
        Returns the counts of each player's club in the team.

        Parameters:
            - gw_data (dict): The data for the gameweek.

        Returns:
            - dict: The counts of each player's club in the team.
        """
        # Get counts of each player's club
        club_counts = {}
        players = self.gks + self.defs + self.mids + self.fwds + [player[0] for player in self.subs]

        for player in players:
            club = str(self.fpl.get_player_team(player, self.gameweek, gw_data))  # Convert club to string
            club_counts[club] = club_counts.get(club, 0) + 1

        return club_counts
    
    def counts_from_list(self, player_list):
        """
        Returns the counts of each player's club in a list of players.

        Parameters:
            - player_list (list): A list of players.

        Returns:
            - dict: The counts of each player's club in the list.
        """
        # Get counts of each player's club
        club_counts = {}
        for player in player_list:
            club = self.fpl.get_player_team(player, self.gameweek)
            club_counts[club] = club_counts.get(club, 0) + 1

        return club_counts
    
    def check_max_from_same_club(self):
        """
        Checks if the team has more than 3 players from the same club.

        Returns:
            bool: True if the team has at most 3 players from the same club, False otherwise.
        """
        club_counts = self.get_club_counts()

        # Check if any club has more than 3 players
        for club in club_counts:
            if club_counts[club] > 3:
                #print(f'Club {club} has {club_counts[club]} players from the same team')
                return False
            
        return True
    
    def auto_chips(self, triple_captain_threshold=8, bench_threshold=4, free_hit_threshold=35, wildcard_threshold=30):
        """
        Automatically activates chips based on the team's performance.

        Parameters:
            - triple_captain_threshold (int): The threshold for activating the Triple Captain chip (default: 8).
            - bench_threshold (int): The threshold for activating the Bench Boost chip (default: 4).
            - free_hit_threshold (int): The threshold for activating the Free Hit chip (default: 35).
            - wildcard_threshold (int): The threshold for activating the Wildcard chip (default: 30).
        """
        
        print('Checking for any chips...' , end='\r')
        if self.season == '2022-23' and (self.gameweek == 7 or self.gameweek == 8):
            return
        xi_xp = self.team_xp(include_subs=False)
        # Triple Captain
        if self.chip_triple_captain_available and not self.any_chip_in_use():
            print('Checking for any chips [Triple Captain]' , end='\r')
            # check if its worth using it
            captain = self.captain
            captain_xp = self.player_xp(captain, self.player_pos(captain))
            #print(f'Captain xP: {captain_xp:.2f}')
            if captain_xp > triple_captain_threshold and self.gameweek > 1:
                print(f'CHIP: Triple Captain activated on GW{self.gameweek} for {captain} with {captain_xp:.2f} xP\n')
                self.chips_used.append(['Triple Captain', self.gameweek])
                self.chip_triple_captain_available = False
                self.chip_triple_captain_active = True

        # Bench Boost
        if self.chip_bench_boost_available and not self.any_chip_in_use():
            print('Checking for any chips [Bench Boost]' , end='\r')
            # check if its worth using it
            all_xp = self.team_xp(include_subs=True)
            bench_xp = all_xp - xi_xp
            #print(f'Bench xP {bench_xp}')
            if bench_xp > bench_threshold and self.gameweek > 1:
                print(f'CHIP: Bench Boost activated on GW{self.gameweek} for {bench_xp:.2f} xP\n')
                self.chips_used.append(['Bench Boost', self.gameweek])
                self.chip_bench_boost_available = False
                self.chip_bench_boost_active = True

        # Free hit
        if self.chip_free_hit_available and not self.any_chip_in_use():
            print('Checking for any chips [Free Hit]' , end='\r')
            if xi_xp < free_hit_threshold:
                self.chip_free_hit_available = False
                self.chip_free_hit_active = True
                self.chips_used.append(['Free Hit', self.gameweek])
                print(f'CHIP: Free Hit activated on GW{self.gameweek} for {xi_xp:.2f} xP\n')
                self.return_subs_to_team()
                self.free_hit_team = [[self.gks, self.defs, self.mids, self.fwds], self.budget, self.gameweek]
                self.initial_team_generator()

        # Wildcard
        if self.chip_wildcard_available and not self.any_chip_in_use():
            print('Checking for any chips [Wildcard]' , end='\r')
            if xi_xp < wildcard_threshold:
                print(f'CHIP: Wildcard activated on GW{self.gameweek} for {xi_xp:.2f} xP\n')
                self.initial_team_generator()
                print(f'Current Team xP {xi_xp:.2f} vs New xP {self.team_xp(include_subs=True):.2f}')
                self.chip_wildcard_available = False
                self.chips_used.append(['Wildcard', self.gameweek])
    
    def any_chip_in_use(self):
        """
        Checks if any chip is currently in use.

        Returns:
            - bool: True if any chip is in use, False otherwise.
        """
        if self.chip_triple_captain_active or self.chip_bench_boost_active or self.chip_free_hit_active:
            return True
        else:
            return False
        
    def load_free_hit_team(self):
        """
        Loads the team from the Free Hit chip.
        """
        pos_players = self.free_hit_team[0]
        budget = self.free_hit_team[1]
        gw = self.free_hit_team[2]
        
        self.return_subs_to_team()

        # Clear Current team
        self.gks = []
        self.defs = []
        self.mids = []
        self.fwds = []
        self.subs = []

        print(f'Loading pre-Free Hit team with from GW{gw}', end='\r')

        # Load the free hit team
        for index, pos in enumerate(pos_players):
            positions = ['GK', 'DEF', 'MID', 'FWD']
            p_pos = positions[index]
            for player in pos:
                #print(f'Player {player} position {p_pos}')
                self.add_player(player, p_pos, 0, force=True)
                
        # Reset budget
        self.budget = budget

        print(f'Loaded pre-Free Hit team {self.budget:.2f} budget remaining', end='\r')

        # Clear free hit team
        self.free_hit_team = None
        
    def team_value(self):
        """
        Returns the total value of the team.

        Returns:
            - float: The total value of the team.
        """
        value = 0
        p_count = 0
        for player in self.gks:
            val = self.player_value(player, self.gw_data)
            if val != None:
                value += val
                p_count += 1
            else:
                if p_count > 0:
                    value += (value / p_count)
                
        for player in self.defs:
            val = self.player_value(player, self.gw_data)
            if val != None:
                value += val
                p_count += 1
            else:
                value += (value / p_count)
        for player in self.mids:
            val = self.player_value(player, self.gw_data)
            if val != None:
                value += val
                p_count += 1
            else:
                value += (value / p_count)
        for player in self.fwds:
            val = self.player_value(player, self.gw_data)
            if val != None:
                value += val
                p_count += 1
            else:
                value += (value / p_count)
        for player in self.subs:
            val = self.player_value(player[0], self.gw_data)
            if val != None:
                value += val
                p_count += 1
            else:
                value += (value / p_count)
            
        return value

    def get_n_gws_xp(self, n, discount_factor):
        """
        Returns the expected points (xP) for the next n gameweeks.

        Parameters:
            - n (int): The number of gameweeks.
            - discount_factor (float): The discount factor for the expected points.

        Returns:
            - float: The expected points for the next n gameweeks.
        """
        if self.gameweek < 36:
            results = self.fpl.discount_next_n_gws(self.combined_xp, self.gameweek, n, discount_factor=discount_factor)
        else:
            results = self.combined_xp
        return results
    
    def pos_price_minimum(self, position):
        """
        Returns the minimum price for a player in a given position.

        Parameters:
            - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
            - float: The minimum price for a player in the position.
        """
        if position == 'GK' or position == 'DEF':
            return 4.0
        elif position == 'MID' or position == 'FWD':
            return 4.5
        else:
            print(f'Invalid position: {position}')
            