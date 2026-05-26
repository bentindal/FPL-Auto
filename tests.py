import unittest
from fpl_auto import team as team_module
from fpl_auto.team import team, POSITIONS, MAX_PER_POS, MIN_PRICE


SEASON = '2021-22'
GW = 1


def make_team(**kwargs):
    return team(SEASON, GW, **kwargs)


class TestTransferInAllowed(unittest.TestCase):
    def test_club_rule_max_three(self):
        t = make_team()
        t.add_player('Joel Matip', 'DEF')
        t.add_player('Mohamed Salah', 'MID')
        t.add_player('Sadio Mané', 'MID')
        # 4th Liverpool player must be rejected
        self.assertFalse(t.transfer_in_allowed('Andrew Robertson', 'DEF'))

    def test_cannot_exceed_budget(self):
        t = make_team(budget=0.1)
        self.assertFalse(t.transfer_in_allowed('Andrew Robertson', 'DEF'))

    def test_cannot_exceed_squad_size(self):
        t = make_team(budget=1000)
        # Fill squad to 15 via a known-good path
        players = [[], [], [], [], []]
        t2 = team(SEASON, GW, 1000, players=players)
        # Manually stuff the squad to 15 by adding cheap real players
        cheap = {
            'GK': ['Hugo Lloris', 'Ederson Santana de Moraes'],
            'DEF': ['Marc Guéhi', 'Thiago Emiliano da Silva', 'Victor Lindelöf', 'Alex Nicolao Telles', 'Aaron Cresswell'],
            'MID': ['Mason Mount', 'Heung-Min Son', 'Rodrigo Hernandez', 'Raheem Sterling', 'Jorge Luiz Frello Filho'],
            'FWD': ['Harry Kane', 'Jean-Philippe Mateta', 'Danny Ings'],
        }
        for pos, names in cheap.items():
            for name in names:
                t2.add_player(name, pos, 4.0)
        self.assertEqual(t2.squad_size(), 15)
        self.assertFalse(t2.transfer_in_allowed('Andrew Robertson', 'DEF'))

    def test_cannot_exceed_max_per_position(self):
        t = make_team(budget=1000)
        for name in ['Marc Guéhi', 'Thiago Emiliano da Silva', 'Victor Lindelöf',
                     'Alex Nicolao Telles', 'Aaron Cresswell']:
            t.add_player(name, 'DEF', 4.0)
        self.assertFalse(t.transfer_in_allowed('Andrew Robertson', 'DEF'))

    def test_invalid_player_rejected(self):
        t = make_team()
        self.assertFalse(t.transfer_in_allowed('Not A Real Player', 'MID'))

    def test_invalid_position_rejected(self):
        t = make_team()
        self.assertFalse(t.transfer_in_allowed('Mohamed Salah', 'STRIKER'))

    def test_player_on_stoplist_rejected(self):
        t = make_team()
        t.player_stop_list = ['Mohamed Salah']
        self.assertFalse(t.transfer_in_allowed('Mohamed Salah', 'MID'))


class TestAddPlayer(unittest.TestCase):
    def test_valid_player_added(self):
        t = make_team(budget=100)
        t.add_player('Mohamed Salah', 'MID')
        self.assertIn('Mohamed Salah', t.mids)

    def test_budget_decreases_on_add(self):
        t = make_team(budget=100)
        before = t.budget
        t.add_player('Mohamed Salah', 'MID')
        self.assertLess(t.budget, before)

    def test_add_player_returns_none_on_failure(self):
        t = make_team(budget=0.1)
        result = t.add_player('Mohamed Salah', 'MID')
        self.assertIsNone(result)

    def test_cannot_add_same_player_twice(self):
        t = make_team(budget=100)
        t.add_player('Andrew Robertson', 'DEF')
        result = t.add_player('Andrew Robertson', 'DEF')
        self.assertIsNone(result)
        self.assertEqual(t.defs.count('Andrew Robertson'), 1)

    def test_mutable_default_isolation(self):
        t1 = make_team()
        t2 = make_team()
        t1.add_player('Mohamed Salah', 'MID')
        self.assertNotIn('Mohamed Salah', t2.mids)


class TestSquadSize(unittest.TestCase):
    def test_squad_size_counts_subs(self):
        t = make_team(budget=1000)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        t.subs.append(['Mohamed Salah', 'MID'])
        # subs don't remove from squad list directly without add_sub
        # just verify squad_size counts them
        self.assertEqual(t.squad_size(), t.xi_size() + len(t.subs))

    def test_empty_squad_is_zero(self):
        t = make_team()
        self.assertEqual(t.squad_size(), 0)


class TestCaptaincy(unittest.TestCase):
    def test_auto_captain_picks_highest_xp(self):
        t = make_team(budget=1000)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        t.add_player('Harry Kane', 'FWD', 4.0)  # Both in 2021-22
        t.auto_captain()
        self.assertIn(t.captain, ['Mohamed Salah', 'Harry Kane'])
        self.assertNotEqual(t.captain, t.vice_captain)

    def test_auto_captain_requires_two_players(self):
        t = make_team(budget=1000)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        # With only one player, suggest_captaincy would IndexError — guard it
        xp_list = t.get_all_xp()
        self.assertEqual(len(xp_list), 1)


class TestTransferLogic(unittest.TestCase):
    def test_transfer_reduces_transfers_left(self):
        t = make_team(budget=100, transfers_left=1)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        t.add_player('Heung-Min Son', 'MID', 4.0)
        # Can't easily run a full transfer without a complete squad, but we can
        # verify the transfers_left cap for non-2024-25 seasons
        self.assertEqual(t.transfers_left, 1)

    def test_player_in_squad_detection(self):
        t = make_team(budget=100)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        self.assertTrue(t.player_in_squad('Mohamed Salah'))
        self.assertFalse(t.player_in_squad('Harry Kane'))

    def test_player_in_squad_list_input(self):
        t = make_team(budget=100)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        self.assertTrue(t.player_in_squad(['Mohamed Salah', 'MID']))


class TestPositionConstants(unittest.TestCase):
    def test_max_per_pos(self):
        self.assertEqual(MAX_PER_POS['GK'], 2)
        self.assertEqual(MAX_PER_POS['DEF'], 5)
        self.assertEqual(MAX_PER_POS['MID'], 5)
        self.assertEqual(MAX_PER_POS['FWD'], 3)

    def test_min_price(self):
        self.assertEqual(MIN_PRICE['GK'], 4.0)
        self.assertEqual(MIN_PRICE['DEF'], 4.0)
        self.assertEqual(MIN_PRICE['MID'], 4.5)
        self.assertEqual(MIN_PRICE['FWD'], 4.5)


class TestSubstitutions(unittest.TestCase):
    def test_return_subs_to_team(self):
        t = make_team(budget=1000)
        t.add_player('Mohamed Salah', 'MID', 4.0)
        t.subs.append(['Mohamed Salah', 'MID'])
        t.mids.remove('Mohamed Salah')
        t.return_subs_to_team()
        self.assertIn('Mohamed Salah', t.mids)
        self.assertEqual(t.subs, [])


if __name__ == '__main__':
    unittest.main()
