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
        - If below certain number of guards, should produce more
    - Worker
        - Dropoff point : where to deload halites
        - Risk taker flag
    - Offense
        - Offense point
        - Search for prey
    - Dropoff

- Should I track opponent's halite?

"""
import hlt
from hlt import constants
from hlt.positionals import Direction
import logging


from constants import *

class NaiveStrategy:

    def __init__(self, game):
        self.game = game
        self.turn = 0
        self.ship_dict = {}
        self.spawn_queue = [] # units to be made
        self.new_ship_queue = [] # newly made ships
        self.setup()

    def setup(self):
        for ship in self.game.me.get_ships():
            if ship.id not in self.ship_dict:
                self.ship_dict[ship.id] = DEFAULT_WORKER
                self.ship_dict[ship.id][DELOAD_POINT] = self.game.me.shipyard.position

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
        # Get in line in 3 directions to deload (how will the line form? like T or fork shape where the fork 
        # is heading relatively empty region)
        # After deloading get out in one way
        # DELOAD_POINT = 'deload_point'
        # RISK_TAKER = 'risk_taker'
        # DEFAULT_STATE = 'default'
        # DELOAD_SHIP : None
        # ACTION_STATE = 'action'
        # RUN_STATE = 'run'
        ship_status = self.ship_dict[ship.id]
        # if opponent near by run:
        if 
        if ship_status[STATUS] == DEFAULT_STATE:
            # go after closest/largest halite
        
        elif ship_status[STATUS] == ACTION_STATE:
            # return to deload point
        
        elif ship_status[STATUS] == RUN_STATE:
            # run in the opposite direction

    
    def handle_guard(self, ship):
        pass

    def handle_offense(self, ship):
        pass

    def handle_dropoff(self, ship):
        pass
    
    def new_ship(self, ship):
        if self.new_ship_queue:
            self.ship_dict[ship.id] = self.new_ship_queue.pop(0)
        else:
            self.ship_dict[ship.id] = DEFAULT_WORKER
            self.ship_dict[ship.id][DELOAD_POINT] = self.game.me.shipyard.position
        return True
    
    def update_ship_dict(self):
        me = self.game.me
        #TODO gather metrics of which ships were lost
        for ship_id in self.ship_dict:
            if not me.has_ship(ship_id):
                if self.ship_dict[ship_id][UNIT_INFO] == WORKER:
                    # Update the dropoff ship's num_worker value.
                    deloading_ship = self.ship_dict[ship_id][DELOAD_SHIP]
                    if deloading_ship:
                        self.ship_dict[deloading_ship.id][NUM_WORKERS] -= 1
                del self.ship_dict[ship_id]

    def update_spawn_queue(self):
        # TODO what type of unit should be spawned?
        
        if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST:
            command_queue.append(me.shipyard.spawn())

    def update_new_ship_queue(self, spawn_info):
        # add to new_ship_queue
        pass
            
            

    def play_turn(self):
        """
        Play a single turn
        """
        self.game.update_frame()
        me = self.game.me
        game_map = self.game.game_map

        self.update_ship_dict()

        # TODO check for some states: Are the good regions taken?        

        command_queue = []
        
        for ship in me.get_ships():
            if ship.id not in self.ship_dict:
                self.new_ship(ship)
            unit_info = self.ship_dict[ship.id][UNIT_INFO]
            move = None
            if unit_info == WORKER:
                move = self.handle_worker(ship)
            elif unit_info == OFFENSE:
                move = self.handle_offense(ship)
            elif unit_info == GUARD:
                move = self.handle_guard(ship)
            elif unit_info == DROPOFF:
                move = self.handle_dropoff(ship)
            command_queue.append(ship.move(move))

        self.update_spawn_queue() # spawn if a certain predicate meets
        if self.spawn_queue and not game_map[me.shipyard].is_occupied:
            self.update_new_ship_queue(self.spawn_queue.pop(0))
            command_queue.append(me.shipyard.spawn())

        self.game.end_turn(command_queue)
        return True

    