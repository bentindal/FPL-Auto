import pandas as pd
import fpl_auto.data as fpl

class team:
    def __init__(self, season, gameweek, budget=100.0, gks=[], defs=[], mids=[], fwds=[]):
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
        self.gks = gks
        self.defs = defs
        self.mids = mids
        self.fwds = fwds
        self.subs = []
        self.gk_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/GK.tsv', sep='\t')
        self.def_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/DEF.tsv', sep='\t')
        self.mid_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/MID.tsv', sep='\t')
        self.fwd_xp = pd.read_csv(f'predictions/{season}/GW{self.gameweek}/FWD.tsv', sep='\t')
        self.gk_player_list = dict(zip(self.gk_xp.Name, self.gk_xp.xP))
        self.def_player_list = dict(zip(self.def_xp.Name, self.def_xp.xP))
        self.mid_player_list = dict(zip(self.mid_xp.Name, self.mid_xp.xP))
        self.fwd_player_list = dict(zip(self.fwd_xp.Name, self.fwd_xp.xP))
        self.gk_xp_dict = dict(zip(self.gk_xp.Name, self.gk_xp.xP))
        self.def_xp_dict = dict(zip(self.def_xp.Name, self.def_xp.xP))
        self.mid_xp_dict = dict(zip(self.mid_xp.Name, self.mid_xp.xP))
        self.fwd_xp_dict = dict(zip(self.fwd_xp.Name, self.fwd_xp.xP))
        self.xp_dict = {**self.gk_xp_dict, **self.def_xp_dict, **self.mid_xp_dict, **self.fwd_xp_dict}
        self.player_name_list = self.gk_xp.Name.tolist() + self.def_xp.Name.tolist() + self.mid_xp.Name.tolist() + self.fwd_xp.Name.tolist()
        self.player_xp_list = self.gk_xp.xP.tolist() + self.def_xp.xP.tolist() + self.mid_xp.xP.tolist() + self.fwd_xp.xP.tolist()
        self.player_list = dict(zip(self.player_name_list, self.player_xp_list))
        self.positions_list = self.fpl.position_dict(self.gameweek)
        self.captain = ''
        self.vice_captain = ''
        self.points_scored = {}
        if self.gameweek < 21:
            self.points_scored = self.fpl.actual_points_dict(season, gameweek)

    def add_player(self, player, position):
        """
        Adds a player to the team.

        Parameters:
        - player (str): The name of the player.
        - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
        - None
        """
        if position not in ['GK', 'DEF', 'MID', 'FWD']:
            print(f'Invalid position {position}')
            return

        position_list = getattr(self, position.lower() + 's')
        if player in self.player_list and len(position_list) < self.get_max_players(position):
            position_list.append(player)
            self.budget -= self.player_value(player)
    
        elif len(position_list) >= self.get_max_players(position):
            print(f'Player {player} {position} max players reached')
        else:
            print(f'Player {player} {position} not found')

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
    
    def remove_player(self, player, position):
        """
        Removes a player from the team.

        Parameters:
        - player (str): The name of the player.
        - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
        - None
        """
        if position == 'GK':
            self.gks.remove(player)
            self.budget += self.player_value(player)
        elif position == 'DEF':
            self.defs.remove(player)
            self.budget += self.player_value(player)
        elif position == 'MID':
            self.mids.remove(player)
            self.budget += self.player_value(player)
        elif position == 'FWD':
            self.fwds.remove(player)
            self.budget += self.player_value(player)
        else:
            print('Invalid position')
    
    def add_sub(self, player, position):
        """
        Adds a substitute player to the team.

        Parameters:
        - player (str): The name of the player.
        - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
        - None
        """
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

    def remove_sub(self, player, position):
        """
        Removes a substitute player from the team.

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
            print('Invalid position, cannot add sub')
            
    def display(self):
        """
        Displays the current team lineup.

        Returns:
        - None
        """
        self.return_subs_to_team()

        self.auto_subs()
        self.auto_captain()

        print(f'GW{self.gameweek}:')
        print(f'GK: {self.gks}')
        print(f'DEF: {self.defs}')
        print(f'MID: {self.mids}')
        print(f'FWD: {self.fwds}')
        print(f'SUBS: {self.subs}')
        print(f'C: {self.captain}, VC: {self.vice_captain}')

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
        # Rank each player by their xP, list the lowest xP first
        ranked_gk = []

        # Return subs to team
        self.return_subs_to_team()

        # Sort players by xP
        for player in self.gks:
            ranked_gk.append([player, self.player_list[player], 'GK'])
        ranked_gk.sort(key=lambda x: float(x[1]))
        ranked_others = []
        for player in self.defs:
            ranked_others.append([player, self.player_list[player], 'DEF'])
        for player in self.mids:
            ranked_others.append([player, self.player_list[player], 'MID'])
        for player in self.fwds:
            ranked_others.append([player, self.player_list[player], 'FWD'])
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
        if position == 'GK':
            xp_dict = self.gk_xp_dict
        elif position == 'DEF':
            xp_dict = self.def_xp_dict
        elif position == 'MID':
            xp_dict = self.mid_xp_dict
        elif position == 'FWD':
            xp_dict = self.fwd_xp_dict

        # return xP for player
        if player in xp_dict:
            return xp_dict[player]
        else:
            print(f'Player {player} {position} not found')
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
            team_xp.append([player, self.player_xp(player, 'GK')])
        for player in self.defs:
            team_xp.append([player, self.player_xp(player, 'DEF')])
        for player in self.mids:
            team_xp.append([player, self.player_xp(player, 'MID')])
        for player in self.fwds:
            team_xp.append([player, self.player_xp(player, 'FWD')])
        if include_subs:
            for player in self.subs:
                team_xp.append([player[0], self.player_xp(player[0], player[1])])

        return team_xp
    
    def squad_size(self):
        return len(self.gks) + len(self.defs) + len(self.mids) + len(self.fwds) + len(self.subs)
    
    def xi_size(self):
        return len(self.gks) + len(self.defs) + len(self.mids) + len(self.fwds)
    
    def team_xp(self):
        """
        Calculates the expected points (xP) for the entire team.

        Returns:
        - float: The total expected points for the team.
        """
        self.return_subs_to_team()
        self.auto_subs()
        self.auto_captain()
        # Get xP for each player in team
        xp_list = self.get_all_xp()
        total_xp = 0
        if self.squad_size() != 15:
            print(f'Team not complete, squad size {self.squad_size()}')
            return 0
        else:
            for player in xp_list:
                if player[0] == self.captain:
                    total_xp += player[1] * 2
                else:
                    total_xp += player[1]

        return total_xp
    
    def player_p(self, player, position):
        """
        Returns the actual points scored by a player in a given position.

        Parameters:
        - player (str): The name of the player.
        - position (str): The position of the player ('GK', 'DEF', 'MID', 'FWD').

        Returns:
        - int: The actual points scored by the player.
        """
        if player in self.points_scored and self.captain == player:
            return self.points_scored[player] * 2
        elif player in self.points_scored:
            return self.points_scored[player]
        else:
            #print(f'Player {player} {position} points not found for GW{self.gameweek} {self.season}!')
            return 0
    
    def get_team_p(self):
        """
        Calculates the actual points scored by the entire team.

        Returns:
        - int: The total actual points scored by the team.
        """
        all_p = 0
        
        for player in self.gks:
            all_p += self.player_p(player, 'GK')
        for player in self.defs:
            all_p += self.player_p(player, 'DEF')
        for player in self.mids:
            all_p += self.player_p(player, 'MID')
        for player in self.fwds:
            all_p += self.player_p(player, 'FWD')

        return all_p
    
    def team_p(self):
        """
        Calculates the actual points scored by the team.

        Returns:
        - int: The total actual points scored by the team.
        """
        self.return_subs_to_team()
        
        self.auto_subs()
        
        self.auto_captain()
        
        self.swap_players_who_didnt_play()

        return self.get_team_p()
    
    def player_value(self, player):
        """
        Returns the price of a player.

        Parameters:
        - player (str): The name of the player.

        Returns:
        - int: The price of the player.
        """
        # Get price for player
        if self.fpl.get_price(self.gameweek, player) != None:
            return self.fpl.get_price(self.gameweek, player)
        else:
            return self.fpl.get_price(self.gameweek - 1, player)
    
    def player_pos(self, player):
        """
        Returns the position of a player.

        Parameters:
        - player (str): The name of the player.

        Returns:
        - str: The position of the player.
        """
        # Get position for player
        if player in self.fpl.position_dict(self.gameweek - 1):
            return self.fpl.position_dict(self.gameweek - 1)[player]
        elif player in self.positions_list:
            return self.positions_list[player]
        else:
            print(f'Player {player} not found in GW{self.gameweek}, {self.season}')
            return None
    
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
        self.captain = captain
        self.vice_captain = vice_captain
    
    def auto_captain(self):
        captain, vice_captain = self.suggest_captaincy()
        self.update_captain(captain, vice_captain)
    
    def suggest_transfer_out(self):
        # Get xP for each player in team
        xp_list = self.get_all_xp(include_subs=True)
        # Sort by xP
        xp_list.sort(key=lambda x: float(x[1]), reverse=False)
        for potential_player in xp_list:
            target_name = potential_player[0]
            target_pos = self.player_pos(target_name)
            target_budget = self.fpl.get_price(self.gameweek, target_name)
            if target_pos != None and target_budget != None:
                return target_name, target_pos, target_budget
            
        return '', '', 0
    
    def suggest_transfer_in(self, position, budget):
        if position == 'GK':
            player_list = self.gk_player_list
        elif position == 'DEF':
            player_list = self.def_player_list
        elif position == 'MID':
            player_list = self.mid_player_list
        elif position == 'FWD':
            player_list = self.fwd_player_list
        else:
            print(f'Invalid position {position}')
            quit()
        # Sort players by xP
        ranked_player_list = []
        for player in player_list:
            ranked_player_list.append([player, player_list[player]])
        ranked_player_list.sort(key=lambda x: float(x[1]), reverse=True)

        # Go through ranked_player_list, find first player that is within the budget and is not already in the team
        for player in ranked_player_list:
            p_cost = self.player_value(player[0])
            if p_cost != None:
                if p_cost <= budget and not self.player_in_squad(player): # and not in team already!
                    return player[0]
        
        print(f'No player found within budget {budget} for position {position}')
        return ''
    
    def player_in_squad(self, player):
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
        
    def transfer(self, transfer_out, transfer_in, position):

        self.return_subs_to_team()
        self.remove_player(transfer_out, position)
        self.add_player(transfer_in, position)
        
    def swap_players_who_didnt_play(self):
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
                    
                    # If sub matches play pos 
                    #print(f'Player: {player} {self.player_pos(player)}, Sub: {sub}')
                    if self.player_pos(player) == sub[1] and sub[0] not in team_nonplayers:
                        
                        # Add sub to team
                        self.remove_sub(sub[0], sub[1])
                        # Remove sub from subs
                        self.subs.remove(sub)
                        # Remove player from team
                        self.add_sub(player, sub[1])
                        # Add player to subs
                        self.subs.append([player, sub[1]])
                        print(f'Swapped {sub[0]} {self.player_p(sub[0], sub[1])} with {player} {self.player_p(player, self.positions_list[player])} (pos match)')
                        
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
                            self.add_sub(player, self.positions_list[player])
                            # Add player to subs
                            self.subs.append([player, self.positions_list[player]])
                            print(f'Swapped {sub[0]} with {player} (no pos match)')
                            sub_made = True
                            break
                            


            


    
    
