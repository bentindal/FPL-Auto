import unittest
from fpl_auto import team

class TestTeam(unittest.TestCase):
    def testMaxThreeFromSameTeam(self):
        t = team.team('2021-22')
        t.add_player('Joel Matip', 'DEF') # Liverpool player 1
        t.add_player('Mohamed Salah', 'MID') # Liverpool player 2
        t.add_player('Sadio Mané', 'MID') # Liverpool player 3
        self.assertFalse(t.add_player('Andrew Robertson', 'DEF')) # Should fail because 3 Liverpool players already

if __name__ == '__main__':
    unittest.main()