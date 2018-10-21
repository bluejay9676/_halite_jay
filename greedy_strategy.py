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
    def __init__(self, game, max_halite, search_radius=50):
        self.game = game
        self.max_halite = max_halite
        self.turn = 1
        self.ships_without_actions = set()
        self.possible_ship_actions = [FORAGE, DELOAD]
        self.possible_shipyard_actions = [SPAWN, IDLE]
        self.possible_directions = [
            Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still
        ]
        self.search_radius = search_radius
        self.ship_status = {} # ship.id --- action, target, closest mine, closest home,
                              #         --- # of enemies around me, sum of distance from the enemies
                              #         --- # of allies around me, sum of distance from the allies
                              #         --- sum of halites in the search area.
        self.targets = []
    
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
                self.ship_status[ship.id][HOME] = closest_home
                self.ship_status[ship.id][DIST_HOME] = closest_home_distance
                num_enemies, sum_dist_enemies, num_allies, \
                    sum_dist_allies, sum_halites, closest_mine, closest_mine_distance = self._search_surrounding(ship, ship.position)

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
        self.targets = []

    def _search_surrounding(self, ship, pos, radii=0):
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

        best_mine = None
        best_mine_distance = 987654321
        best_net_profit = -987654321

        sec_best_mine = None
        sec_best_mine_distance = None
        sec_best_net_profit = -987654321       

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
                home_pos = self.ship_status[ship.id][HOME].position
                net_profit = (ship.halite_amount * (0.9 ** dist) + \
                    curr_cell.halite_amount * 1.2) * (0.9 ** game_map.calculate_distance(new_pos, home_pos))
                if net_profit > best_net_profit and curr_cell not in self.targets:
                    best_net_profit = net_profit
                    best_mine = curr_cell
                    best_mine_distance = dist
                if net_profit > sec_best_net_profit: 
                    sec_best_mine = curr_cell
                    sec_best_mine_distance = dist
                    sec_best_net_profit = net_profit
                sum_halites += curr_cell.halite_amount
        if best_mine is None:
            best_mine = sec_best_mine
            best_mine_distance = sec_best_mine_distance
        else:
            self.targets.append(best_mine)
        return num_enemies, sum_dist_enemies, num_allies, sum_dist_allies, \
            sum_halites, best_mine, best_mine_distance

    def evaluate_action(self, ship):
        dist_closest_home = self.ship_status[ship.id][DIST_HOME]
        current_halite = ship.halite_amount
        halite_when_home = (current_halite * 1.2) * (0.9 ** dist_closest_home)
        return halite_when_home

    def evaluate_direction(self, ship, move):
        me = self.game.me
        game_map = self.game.game_map

        target = self.ship_status[ship.id][TARGET]
        pos_after_move = ship.position.directional_offset(move)
        halite_after_move = game_map[pos_after_move].halite_amount * 0.25 + \
                                ship.halite_amount * 0.9
        distance_target = game_map.calculate_distance(pos_after_move, target.position)
        if move == Direction.Still:
            halite_after_move = ship.halite_amount

        # TODO add bonus point calculation
        # num_enemies, sum_dist_enemies, num_allies,\
        # sum_dist_allies, sum_halites, closest_mine, closest_mine_distance \
        # = self._search_surrounding(pos_after_move, 20)

        score = halite_after_move * 10 + \
            -distance_target * 5000
            # int(check_collision) * -1000000
            # num_enemies * -3 + \
            # num_allies * 3 + sum_halites * 2
        return score

    def evaluate_spawn(self):
        me = self.game.me
        game_map = self.game.game_map
        num_ships = len(self.ship_status)
        # TODO halites currently possess?
        cost_per_ship = num_ships ** 1.67 if num_ships <= 7 else num_ships ** 2.2
        profit_per_ship = 100 if num_ships <= 5 else (num_ships * 25 - self.turn * 0.3)
        net_profit_spawn = profit_per_ship - cost_per_ship
        return net_profit_spawn


    def calculate_move(self, ship, action):
        me = self.game.me
        game_map = self.game.game_map
        
        best_move = Direction.Still # (k, v)  k = {x: x in (Direction, Switch unit)}
        best_score = -987654321
        # Evaluate directionals
        if action == FORAGE or action == DELOAD:
            for move in self.possible_directions:
                pos_after_move = ship.position.directional_offset(move)
                score = self.evaluate_direction(ship, move)
                if score > best_score and not game_map[pos_after_move].is_occupied:
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
        # TODO Calculate and sort.
        # score_thres = self.turn

        # greedy_order = [] # (ship, action, score) pair
        # while len(self.ships_without_actions) > 0:
        #     best_ship = None
        #     best_action = None
        #     best_score = -987654321
        #     for ship in self.ships_without_actions:
        #         # TODO cache best action for each ship and recalculated it only 
        #         # when evaluation value for that action changed
        #         # for action in self.possible_ship_actions:
        #         score = self.evaluate_action(ship)
        #         if score > best_score:
        #             best_score = score
        #             best_ship = ship
        #             best_action = FORAGE if score < 10 else DELOAD
        #     logging.info('Ship {} has {} halites'.format(best_ship.id, best_ship.halite_amount))
        #     logging.info('Action for {} : {}'.format(best_ship.id, best_action))
        #     self.ship_status[best_ship.id][TARGET] = \
        #         self.ship_status[best_ship.id][MINE] if best_action == FORAGE else self.ship_status[best_ship.id][HOME]
        #     self.ship_status[best_ship.id][ACTION] = best_action
        #     greedy_order.append((best_ship, best_action))
        #     self.ships_without_actions.remove(best_ship)
        ship_score = [(ship, self.evaluate_action(ship)) for ship in me.get_ships()]
        ship_score = sorted(ship_score, key=lambda x: -x[1])
        greedy_order = []
        for ship, score in ship_score:
            action = FORAGE if score < 12 else DELOAD
            self.ship_status[ship.id][TARGET] = \
                self.ship_status[ship.id][MINE] if action == FORAGE else self.ship_status[ship.id][HOME]
            self.ship_status[ship.id][ACTION] = action
            greedy_order.append((ship, action))
            logging.info('Ship {} has {} halites'.format(ship.id, ship.halite_amount))
            logging.info('Action for {} : {}'.format(ship.id, action))

        command_queue = []
        # Calculate moves
        for ship, action in greedy_order:
            best_move = self.calculate_move(ship, action)
            command_queue.append(best_move)

        do_spawn = self.evaluate_spawn() > 0
        if do_spawn and not game_map[me.shipyard].is_occupied and me.halite_amount >= constants.SHIP_COST:
            logging.info("Shipyard will spawn...")
            command_queue.append(me.shipyard.spawn())
            

        # Postprocessing
        self.postprocess()
        logging.info("Current Halite {}".format(me.halite_amount))
        # End the game
        self.game.end_turn(command_queue)
        

    