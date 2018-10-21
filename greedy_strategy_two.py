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
NET_PROF = 'net_profit'

## Actions for ships
FORAGE = 'forage'
DELOAD = 'deload'
# DROPOFF = 'dropoff' # switch to dropoff

## Action for shipyard
SPAWN = 'spawn'
IDLE = 'idle'

class GreedyStrategy:
    def __init__(self, game, max_halite, search_radius=80):
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
        self.targets = {} # ship.id : pos
    
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
                        ACTION : FORAGE,
                        TARGET : None,
                        MINE : None,
                        HOME : None,
                        DIST_MINE : None,
                        DIST_HOME : None,
                        NUM_ENEMIES : None,
                        NUM_ALLIES : None,
                        MEAN_DIST_ENE : None,
                        MEAN_DIST_ALL : None,
                        SUM_HAL : None,
                        NET_PROF : None
                    }

        # 2. Update the ship status dict
        for ship_id in list(self.ship_status.keys()):
            if not me.has_ship(ship_id):
                logging.info("Ship {} has been lost.".format(ship_id))
                self.ship_status.pop(ship_id, None)
                self.targets.pop(ship_id, None)
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
                    sum_dist_allies, sum_halites = self._search_surrounding(ship, self.search_radius)

                self.ship_status[ship.id][NUM_ENEMIES] = num_enemies
                self.ship_status[ship.id][NUM_ALLIES] = num_allies
                self.ship_status[ship.id][MEAN_DIST_ALL] = sum_dist_allies / num_allies if num_allies else 987654321
                self.ship_status[ship.id][MEAN_DIST_ENE] = sum_dist_enemies / num_enemies if num_enemies else 987654321
                self.ship_status[ship.id][SUM_HAL] = sum_halites

    
    def postprocess(self):
        self.turn += 1

    def _search_surrounding(self, ship, radii):
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
        me = self.game.me
        game_map = self.game.game_map
        
        num_enemies = 0
        sum_dist_enemies = 0
        num_allies = 0
        sum_dist_allies = 0
        sum_halites = 0

        best_mine = None
        best_mine_distance = 987654321
        best_net_profit = -987654321 

        home_pos = self.ship_status[ship.id][HOME].position
        curr_pos = ship.position
        for i in range(-round(radii / 2), round(radii / 2), 1): 
            for j in range(-round(radii / 2), round(radii / 2), 1):
                new_pos = curr_pos + positionals.Position(i, j)
                dist = game_map.calculate_distance(curr_pos, new_pos)
                curr_cell = game_map[new_pos]
                curr_halite_amount = curr_cell.halite_amount
                if not curr_cell.is_empty:
                    if (curr_cell.has_structure and curr_cell.structure.owner == me.id) \
                        or (curr_cell.is_occupied and curr_cell.ship.owner == me.id):
                        num_allies += 1
                        sum_dist_allies += dist
                    else: # enemy
                        num_enemies += 1
                        sum_dist_enemies += dist
                sum_halites += curr_halite_amount
                
                if self.ship_status[ship.id][ACTION] == FORAGE and (ship.position == home_pos or not self.targets.get(ship.id)):
                    # normalized_halite_amount = curr_halite_amount * 1.2 if curr_halite_amount >= self.max_halite / 2 else curr_halite_amount
                    net_profit = (ship.halite_amount * 0.1) + \
                        curr_halite_amount * (0.9 ** game_map.calculate_distance(new_pos, home_pos))
                    if net_profit >= 20 and net_profit > best_net_profit and curr_cell not in self.targets.values():
                        best_net_profit = net_profit
                        best_mine = curr_cell
                        best_mine_distance = dist
        
        if best_mine:
            self.targets[ship.id] = best_mine
            self.ship_status[ship.id][MINE] = best_mine
            self.ship_status[ship.id][DIST_MINE] = best_mine_distance
            self.ship_status[ship.id][NET_PROF] = best_net_profit
        return num_enemies, sum_dist_enemies, num_allies, sum_dist_allies, \
            sum_halites

    def evaluate_action(self, ship):
        """
        return 1 if should forage else 0
        """
        # Forage:
        #   group with or
        #   - Previous action was FORAGE and the ship is not at its mine.
        #   - Previous action was FORAGE and the ship is at its mine and the mine not close to empty.
        #   - ship is at home.
        # Deload:
        #   - Previous action was FORAGE and the ship is at its mine and the mine close to empty.
        #   - Incoming enemy ship.
        dist_home = self.ship_status[ship.id][DIST_HOME]
        is_prev_action_forage = int(self.ship_status[ship.id][ACTION] == FORAGE)
        is_at_mine = int(self.ship_status[ship.id][MINE].position == ship.position)
        is_at_home = int(self.ship_status[ship.id][HOME].position == ship.position)
        mine_halite = self.ship_status[ship.id][MINE].halite_amount
        num_enemies, sum_dist_enemies, num_allies, sum_dist_allies, \
            sum_halites = self._search_surrounding(ship, 4)
        incoming_enemy_ship = num_enemies
        halite_left = ship.halite_amount
        is_forage = (
            (is_prev_action_forage and not is_at_mine) or
            (is_prev_action_forage and is_at_mine and mine_halite > 0) or
            is_at_home or 
            (halite_left * (0.9 ** dist_home) <= 0)
        ) and not incoming_enemy_ship
        if is_forage:
            expected_profit = self.ship_status[ship.id][NET_PROF] * 0.95
            return expected_profit * 1000
        else: # deload
            dist_closest_home = self.ship_status[ship.id][DIST_HOME]
            current_halite = ship.halite_amount
            halite_when_home = (current_halite * 1.2) * (0.9 ** dist_closest_home)
            return halite_when_home


    def evaluate_direction(self, ship, move, action):
        me = self.game.me
        game_map = self.game.game_map

        target = self.ship_status[ship.id][TARGET]
        pos_after_move = ship.position.directional_offset(move)
        halite_after_move = ship.halite_amount - game_map[ship.position].halite_amount * 0.1
        distance_target = game_map.calculate_distance(pos_after_move, target.position)
        if move == Direction.Still:
            halite_after_move = game_map[pos_after_move].halite_amount * 0.25 + \
                                ship.halite_amount
        score = halite_after_move * 10 + -distance_target * 5000
        return score

    def calculate_move(self, ship, action):
        me = self.game.me
        game_map = self.game.game_map
        
        best_move = Direction.Still
        best_score = -987654321
        
        # TODO If switching to dropoff

        # Evaluate directionals
        if (game_map[ship.position].halite_amount != 0 and ship.halite_amount <= game_map[ship.position].halite_amount / 10) \
            or (action == FORAGE and ship.position == self.ship_status[ship.id][MINE].position):
            best_move = Direction.Still
        else:
            for move in self.possible_directions:
                pos_after_move = ship.position.directional_offset(move)
                score = self.evaluate_direction(ship, move, action)
                if score > best_score and not game_map[pos_after_move].is_occupied:
                    best_move = move
                    best_score = score
        pos_after_move = ship.position.directional_offset(best_move)
        logging.info("Ship {} was at {} will do {} and be at {}".format(ship.id, ship.position, best_move, pos_after_move))
        game_map[pos_after_move].mark_unsafe(ship)
        return ship.move(best_move)


    def evaluate_spawn(self):
        me = self.game.me
        game_map = self.game.game_map
        num_ships = len(self.ship_status)
        # TODO halites currently possess?
        # cost_per_ship = num_ships ** 1.67 if num_ships <= 7 else num_ships ** 2.2
        cost_per_ship = 0 if num_ships <= 16 else 987654321
        profit_per_ship = 100 if num_ships <= 16 else (num_ships * 25 - self.turn * 0.25)
        net_profit_spawn = profit_per_ship - cost_per_ship
        return net_profit_spawn


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
        ship_score = [(ship, self.evaluate_action(ship)) for ship in me.get_ships()]
        ship_score = sorted(
            ship_score, 
            key=lambda x: (
                not(x[0].halite_amount < game_map[x[0].position].halite_amount / 10 \
                and x[0].position != self.ship_status[x[0].id][HOME].position),
                not(x[0].position == self.ship_status[x[0].id][TARGET].position \
                if self.ship_status[x[0].id][TARGET] else 0),
                -x[1],
            )
        )
        # sorted as following order
        # [can't move][forage target][forage omw][deload home][deload omw]
        greedy_order = []
        for ship, score in ship_score:
            logging.info('Ship {} has score {}'.format(ship.id, score))
            action = FORAGE if score >= 2000 else DELOAD
            self.ship_status[ship.id][TARGET] = \
                self.ship_status[ship.id][MINE] if action == FORAGE else self.ship_status[ship.id][HOME]
            self.ship_status[ship.id][ACTION] = action
            self.targets.pop(ship.id, None)
            greedy_order.append((ship, action))
            logging.info('Ship {} has {} halites'.format(ship.id, ship.halite_amount))
            logging.info('Action for {} : {}'.format(ship.id, action))
            logging.info('Ship {}s target : {}'.format(ship.id, self.ship_status[ship.id][TARGET].position))

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
        

    