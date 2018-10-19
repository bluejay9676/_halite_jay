"""
Naive Strategy

- Create dropoff at a region with dense population of halite
    - When
    - How
    - Security
- Steal opponent's dropoff
    - When
    - How
    - How will you guard the drop off point
- Each ship 
    - is matched to a dropoff point(this includes shipyard)
    - Aggressive flag set. If aggressive -> attack (Perhaps a guard unit?)
    - RiskTaker flag set. If risktaker -> go for the bonus
    - can run away when necessary (in other words, there's a method)
- Safe / Efficient navigation
    - Non collision
    - Fastest

Questions:
- Unit categories? (Saved as dictionary with format)
    - Guard
        - Guard point (near dropoff points) 

    - Worker
        - Dropoff point : where to deload halites
        - Risk taker flag
    - Offense
        - Offense point
        - Search for prey
    - Dropoff

- Should I track opponent's halite?

"""

from constants import *

class NaiveStrategy:

    def __init__(self, game):
        self.game = game
        self.turn = 0
        self.ship_dict = {}
        self.new_ship_queue = [] # contains formated dict

    def halite_rich_regions(self):
        """
        return list of halite full regions or regions that could be attacked
        TODO function that determines whether it's worth to steal the dropoff
        """
        pass

    def run(self, ship):
        """
        run away in the opposite direction of the approaching offense
        """
        pass

    def smart_navigation(self, ship):
        pass

    def handle_worker(self, ship):
        pass
    
    def handle_guard(self, ship):
        pass

    def handle_offense(self, ship):
        pass
    
    def new_ship(self, ship):
        self.ship_dict[ship.id] = self.new_ship_queue.pop(0)
        return True
    

    def play_turn(self):
        """
        Play a single turn
        """
        self.game.update_frame()
        me = self.game.me
        game_map = self.game.game_map

        command_queue = []
        
        for ship in me.get_ships():

        # if the ship not in ship_dict -> new_ship(ship)

        self.game.end_turn(command_queue)
        return True

    