"""
Greedy strategy

Actions
    - Grab resource
    - Go back to deload
    - Switch to dropoff
    - * Attack

"""
import hlt
from hlt import constants, positionals
from hlt.positionals import Direction
import logging

## Macros
ACTION = 'action'
TARGET = 'target'
MINE = 'mine'
HOME = 'home'
DIST_MINE = 'dist_from_mine'
DIST_HOME = 'dist_from_home'
NUM_ENEMIES = 'num_enemies'
NUM_ALLIES = 'num_allies'
MEAN_DIST_ENE = 'mean_dist_enemies'
MEAN_DIST_ALL = 'mean_dist_allies'
SUM_HAL = 'sum_halites'

## Actions for ships
FORAGE = 'forage'
DELOAD = 'deload'
# DROPOFF = 'dropoff' # switch to dropoff

## Action for shipyard
SPAWN = 'spawn'
IDLE = 'idle'

class GreedyStrategy:
    def __init__(self, game,  halite_search_thres, max_halite, search_radius=30):
        self.game = game
        self.max_halite = max_halite
        self.turn = 1
        self.ships_without_actions = set()
        self.possible_ship_actions = [FORAGE, DELOAD]
        self.possible_shipyard_actions = [SPAWN, IDLE]
        self.possible_directions = [
            Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still
        ]
        self.halite_search_thres = halite_search_thres
        self.search_radius = search_radius
        self.good_mine_positions = set()
        self.ship_status = {} # ship.id --- action, target, closest mine, closest home,
                              #         --- # of enemies around me, sum of distance from the enemies
                              #         --- # of allies around me, sum of distance from the allies
                              #         --- sum of halites in the search area.
    
    def preprocess(self):
        me = self.game.me
        game_map = self.game.game_map

        logging.info("Preprocessing...")
        # 1. Add all ships to ships_without_actions
        self.ships_without_actions = set(me.get_ships())

        for ship in me.get_ships():
            if ship.id not in self.ship_status:
                logging.info("Ship {} has been found.".format(ship.id))
                self.ship_status[ship.id] = {
                    ACTION : None,
                    TARGET : None
                }

        # 2. Update the ship status dict
        for ship_id in list(self.ship_status.keys()):
            if not me.has_ship(ship_id):
                logging.info("Ship {} has been lost.".format(ship_id))
                del self.ship_status[ship_id]
            else:
                ship = me.get_ship(ship_id)
                closest_home = me.shipyard
                closest_home_distance = game_map.calculate_distance(ship.position, me.shipyard.position)
                for dropoff in me.get_dropoffs():
                    distance = game_map.calculate_distance(ship.position, dropoff.position)
                    if distance < closest_home_distance:
                        closest_home = dropoff
                        closest_home_distance = distance
                num_enemies, sum_dist_enemies, num_allies, \
                    sum_dist_allies, sum_halites, closest_mine, closest_mine_distance = self._search_surrounding(ship.position)

                self.ship_status[ship.id] = {
                    ACTION : self.ship_status[ship.id][ACTION],
                    TARGET : self.ship_status[ship.id][TARGET],
                    MINE : closest_mine,
                    HOME : closest_home,
                    DIST_MINE : closest_mine_distance,
                    DIST_HOME : closest_home_distance,
                    NUM_ENEMIES : num_enemies,
                    NUM_ALLIES : num_allies,
                    MEAN_DIST_ENE : sum_dist_enemies / num_enemies if num_enemies else 987654321,
                    MEAN_DIST_ALL : sum_dist_allies / num_allies if num_allies else 987654321,
                    SUM_HAL : sum_halites
                }

    
    def postprocess(self):
        self.turn += 1

    def _search_surrounding(self, pos, radii=0):
        """
        Search within the radii for
        1. # of enemies around me 
        2. sum of distance from the enemies
        3. # of allies around me
        4. sum of distance from the allies
        5. sum of halites in the search area,
        6. closest mine with acceptable amount of halites.

        and update ship_status
        """
        if not radii:
            radii = self.search_radius
        me = self.game.me
        game_map = self.game.game_map
        # game_map[position]
        # ship.owner match player_id?
        num_enemies = 0
        sum_dist_enemies = 0
        num_allies = 0
        sum_dist_allies = 0
        sum_halites = 0
        closest_mine = None
        closest_mine_distance = 987654321

        for i in range(-round(radii / 2), round(radii / 2), 1): 
            for j in range(-round(radii / 2), round(radii / 2), 1):
                new_pos = pos + positionals.Position(i, j)
                dist = game_map.calculate_distance(pos, new_pos)
                curr_cell = game_map[new_pos]
                if not curr_cell.is_empty:
                    if (curr_cell.has_structure and curr_cell.structure.owner == me.id) \
                        or (curr_cell.is_occupied and curr_cell.ship.owner == me.id):
                        num_allies += 1
                        sum_dist_allies += dist
                    else: # enemy
                        num_enemies += 1
                        sum_dist_enemies += dist
                else:
                    if curr_cell.halite_amount > self.halite_search_thres:
                        if dist < closest_mine_distance:
                            closest_mine_distance = dist
                            closest_mine = curr_cell
                sum_halites += curr_cell.halite_amount
        return num_enemies, sum_dist_enemies, num_allies, sum_dist_allies, sum_halites, closest_mine, closest_mine_distance

    def evaluate_action(self, ship, action):
        dist_closest_mine = self.ship_status[ship.id][DIST_MINE]
        dist_closest_home = self.ship_status[ship.id][DIST_HOME]
        current_halite = ship.halite_amount
        if action == FORAGE:
            return -dist_closest_mine * 10 + -current_halite * 5
        elif action == DELOAD:
            return -dist_closest_home * 10 + int(current_halite >= self.max_halite / 4 or ship.is_full) * 1000 + int(dist_closest_home == 0) * -10000

    def evaluate_direction(self, ship, move):
        me = self.game.me
        game_map = self.game.game_map

        target = self.ship_status[ship.id][TARGET]
        pos_after_move = ship.position.directional_offset(move)
        halite_after_move = game_map[pos_after_move].halite_amount * 0.25 + \
                                ship.halite_amount * 0.9
        distance_target = game_map.calculate_distance(pos_after_move, target.position)
        check_collision = game_map[pos_after_move].is_occupied

        # TODO add bonus point calculation
        num_enemies, sum_dist_enemies, num_allies,\
        sum_dist_allies, sum_halites, closest_mine, closest_mine_distance \
        = self._search_surrounding(pos_after_move, 4)

        score = halite_after_move * 5 + \
            -distance_target * 10 + \
            int(check_collision) * -10000 + \
            num_enemies * -5 + \
            num_allies * 5 + sum_halites * 2
        return score

    def evaluate_spawn(self):
        me = self.game.me
        game_map = self.game.game_map
        return int(me.halite_amount >= constants.SHIP_COST) * 10 + (1 if self.turn <= 100 else -1) * 15 + me.halite_amount * 5 + \
            int(game_map[me.shipyard].is_occupied) * -10000 + int(me.halite_amount < constants.SHIP_COST) * -10000

    def calculate_move(self, ship, action):
        me = self.game.me
        game_map = self.game.game_map
        
        best_move = None # (k, v)  k = {x: x in (Direction, Switch unit)}
        best_score = -987654321
        # Evaluate directionals
        if action == FORAGE or action == DELOAD:
            for move in self.possible_directions:
                score = self.evaluate_direction(ship, move)
                if score > best_score:
                    best_move = move
                    best_score = score
            pos_after_move = ship.position.directional_offset(best_move)
            game_map[pos_after_move].mark_unsafe(ship)
            return ship.move(best_move)

        # TODO If switching to dropoff

        game_map[ship.position].mark_unsafe(ship)
        return ship.stay_still()

    def play_turn(self):
        """
        Play a single turn
        """
        self.game.update_frame()
        me = self.game.me
        game_map = self.game.game_map


        # Preprocess
        self.preprocess()

        # Calculate orders
        greedy_order = [] # (ship, action) pair
        while len(self.ships_without_actions) > 0:
            best_ship = None
            best_action = None
            best_score = -987654321
            for ship in self.ships_without_actions:
                # TODO cache best action for each ship and recalculated it only 
                # when evaluation value for that action changed
                for action in self.possible_ship_actions:
                    score = self.evaluate_action(ship, action)
                    logging.info('Score when {} does {} : {}'.format(ship.id, action, score))
                    if score > best_score:
                        best_score = score
                        best_ship = ship
                        best_action = action
            logging.info('Action for {} : {}'.format(best_ship.id, best_action))
            self.ship_status[best_ship.id][TARGET] = \
                self.ship_status[best_ship.id][MINE] if best_action == FORAGE else self.ship_status[best_ship.id][HOME]
            logging.info('Target for {} : {}'.format(best_ship.id, self.ship_status[best_ship.id][TARGET]))
            self.ship_status[best_ship.id][ACTION] = best_action
            greedy_order.append((best_ship, best_action))
            self.ships_without_actions.remove(best_ship)

        command_queue = []
        # Calculate moves
        for ship, action in greedy_order:
            logging.info('Ship {} at {}'.format(ship.id, ship.position))
            best_move = self.calculate_move(ship, action)
            logging.info('Move for {} : {}'.format(ship.id, best_move))
            command_queue.append(best_move)

        do_spawn = self.evaluate_spawn() > 0
        if do_spawn:
            logging.info("Shipyard will spawn...")
            command_queue.append(me.shipyard.spawn())
            

        # Postprocessing
        self.postprocess()

        # End the game
        self.game.end_turn(command_queue)
        

    