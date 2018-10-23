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
MINE_ARCHIVE = 'mine_amount'
MINE = 'mine'
HOME = 'home'
NUM_ENEMIES = 'num_enemies'
NUM_ALLIES = 'num_allies'
MEAN_DIST_ENE = 'mean_dist_enemies'
MEAN_DIST_ALL = 'mean_dist_allies'
SUM_HAL = 'sum_halites'
INTERNAL_ID = 'internal_id'

## Actions for ships
FORAGE = 'forage'
DELOAD = 'deload'
DROPOFF = 'dropoff' # switch to dropoff

## Action for shipyard
SPAWN = 'spawn'
IDLE = 'idle'

class GreedyStrategy:
    def __init__(self, game, max_halite, search_radius=70):
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
                              #         --- TODO internal id
        self.mine_targets = {} # ship.id : pos
        self.next_positions = {} # ship.id : pos
        self.merge_flag = False
        self.num_spawn = 0
    
    def preprocess(self):
        me = self.game.me
        game_map = self.game.game_map

        logging.info("Preprocessing...")
        # 1. Add all ships to ships_without_actions
        self.ships_without_actions = set(me.get_ships())

        i = 0
        for ship in me.get_ships():
            if ship.id not in self.ship_status:
                logging.info("Ship {} has been found.".format(ship.id))
                self.ship_status[ship.id] = {
                        ACTION : FORAGE,
                        TARGET : None,
                        MINE : None,
                        MINE_ARCHIVE : 0,
                        HOME : None,
                        NUM_ENEMIES : None,
                        NUM_ALLIES : None,
                        MEAN_DIST_ENE : None,
                        MEAN_DIST_ALL : None,
                        SUM_HAL : None,
                        INTERNAL_ID : None
                    }
            self.ship_status[ship.id][INTERNAL_ID] = i
            i += 1
            

        # 2. Update the ship status dict
        for ship_id in list(self.ship_status.keys()):
            if not me.has_ship(ship_id):
                logging.info("Ship {} has been lost.".format(ship_id))
                self.ship_status.pop(ship_id, None)
                self.mine_targets.pop(ship_id, None)
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
                num_enemies, sum_dist_enemies, num_allies, \
                    sum_dist_allies, sum_halites = self._search_surrounding(ship, self.search_radius)

                self.ship_status[ship.id][NUM_ENEMIES] = num_enemies
                self.ship_status[ship.id][NUM_ALLIES] = num_allies
                self.ship_status[ship.id][MEAN_DIST_ALL] = sum_dist_allies / num_allies if num_allies else 987654321
                self.ship_status[ship.id][MEAN_DIST_ENE] = sum_dist_enemies / num_enemies if num_enemies else 987654321
                self.ship_status[ship.id][SUM_HAL] = sum_halites

    
    def postprocess(self):
        self.turn += 1
        self.next_positions = {}
        if self.turn >= constants.MAX_TURNS - 20:
            self.merge_flag = True

    def check_if_valid_mine(self, ship):
        pass

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
        best_amount = 0

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
                # Update mine only when
                # 1. Deloading
                # 2. Newly made ship
                # 3. The current mine is deprecated
                if self.ship_status[ship.id][ACTION] == DELOAD or (self.ship_status[ship.id][ACTION] == FORAGE and \
                    (self.ship_status[ship.id][MINE] is None or self.ship_status[ship.id][MINE].halite_amount == 0)):
                    dist_mine_home = game_map.calculate_distance(new_pos, home_pos) + 1
                    net_profit = (ship.halite_amount * (0.8 ** (dist + 1)) + curr_halite_amount) * (0.8 ** dist_mine_home)
                    # TODO use check_if_valid_mine that returns net_profit if its valid.
                    if net_profit > best_net_profit and curr_cell not in self.mine_targets.values():
                        best_net_profit = net_profit
                        best_mine = curr_cell
                        best_mine_distance = dist
                        best_amount = curr_halite_amount
        if best_mine:
            self.mine_targets[ship.id] = best_mine
            self.ship_status[ship.id][MINE] = best_mine
            self.ship_status[ship.id][MINE_ARCHIVE] = best_amount
        return num_enemies, sum_dist_enemies, num_allies, sum_dist_allies, \
            sum_halites

    def evaluate_dropoff(self, ship):
        """
        1 if this ship should become a dropoff or not. 0 otherwise
        """
        # Check if other ships that are trying to become a dropoff before this ship.
        # Check if considering the above, there is still a lack of dropoff.
        # If yes -> dropoff
        # otherwise -> keep foraging / deloading.
        return 

    def evaluate_offense(self, ship):
        # TODO should I be offensive or not?
        pass

    def evaluate_action(self, ship):
        me = self.game.me
        game_map = self.game.game_map

        mine = self.ship_status[ship.id][MINE]
        home = self.ship_status[ship.id][HOME]
        distance_here_mine = game_map.calculate_distance(ship.position, mine.position) + 1
        distance_here_home = game_map.calculate_distance(ship.position, home.position) + 1
        distance_mine_home = game_map.calculate_distance(mine.position, home.position) + 1
        mine_halite_amount = game_map[mine.position].halite_amount
        curr_halite_amount = ship.halite_amount

        if self.merge_flag:
            # should always return negative
            return -distance_here_home

        # Exceptional cases
        at_mine = int(distance_here_mine == 1 and mine.halite_amount > 20) * 2000
        deload_flag = curr_halite_amount == self.max_halite
        forage_flag = curr_halite_amount == 0

        expected_profit_forage = (curr_halite_amount * (0.6 ** distance_here_mine) + mine_halite_amount) * (0.7 ** distance_mine_home) + at_mine + forage_flag * 10000 
        expected_profit_deload = curr_halite_amount * (0.8 ** distance_here_home) + deload_flag * 10000

        return expected_profit_forage - expected_profit_deload


    def evaluate_direction(self, ship, move, action):
        me = self.game.me
        game_map = self.game.game_map

        target = self.ship_status[ship.id][TARGET]
        pos_after_move = ship.position.directional_offset(move)
        halite_after_move = ship.halite_amount - game_map[ship.position].halite_amount * 0.1

        ship.halite_amount <= game_map[ship.position].halite_amount / 10
        curr_dist_target = game_map.calculate_distance(ship.position, target.position) + 1
        after_distance_target = game_map.calculate_distance(pos_after_move, target.position) + 1
        next_pos_halite_cost = game_map[pos_after_move].halite_amount
        if move == Direction.Still:
            halite_after_move = game_map[pos_after_move].halite_amount * 0.25 + \
                                ship.halite_amount
        if action == FORAGE and curr_dist_target == 1 and target.halite_amount > 20:
            halite_after_move *= 10000
            next_pos_halite_cost *= -10
        score = halite_after_move * 50 + -next_pos_halite_cost * 2 + -after_distance_target * 3400
        return score

    def calculate_move(self, ship, action):
        me = self.game.me
        game_map = self.game.game_map
        
        best_move = Direction.Still
        best_score = -987654321
        
        # TODO If switching to dropoff
        
        target = self.ship_status[ship.id][TARGET]

        # Evaluate directionals
        for move in self.possible_directions:
            pos_after_move = ship.position.directional_offset(move)
            score = self.evaluate_direction(ship, move, action)
            can_pay_cost = ship.halite_amount >= game_map[ship.position].halite_amount / 10 if move != Direction.Still else True
            is_collision_free = pos_after_move not in self.next_positions.values()
            if self.merge_flag and pos_after_move == self.ship_status[ship.id][HOME].position:
                is_collision_free = True
                score = 987654321
            if score > best_score and is_collision_free and can_pay_cost:
                best_move = move
                best_score = score

        pos_after_move = ship.position.directional_offset(best_move)
        self.next_positions[ship.id] = pos_after_move
        logging.info("Ship {} was at {} will do {} and be at {}".format(ship.id, ship.position, best_move, pos_after_move))
        return ship.move(best_move)


    def evaluate_spawn(self):
        me = self.game.me
        game_map = self.game.game_map
        num_homes = 1 + len(me.get_dropoffs())
        num_ships = len(self.ship_status) # Should always be even number for each HOME.
        return num_ships < num_homes * 10


    def play_turn(self):
        """
        Play a single turn
        """
        self.game.update_frame()
        me = self.game.me
        game_map = self.game.game_map

        def can_pay_cost(ship):
            return ship.halite_amount >= game_map[ship.position].halite_amount / 10
        # Preprocess
        self.preprocess()

        # Calculate orders
        ship_score = [(ship, self.evaluate_action(ship)) for ship in me.get_ships()]
        ship_score = sorted(ship_score, key=lambda x: (can_pay_cost(x[0]), -x[1]))
        greedy_order = []
        for ship, score in ship_score:
            logging.info('Ship {} has score {}'.format(ship.id, score))
            action = FORAGE if score > 0 else DELOAD
            self.ship_status[ship.id][TARGET] = \
                self.ship_status[ship.id][MINE] if action == FORAGE else self.ship_status[ship.id][HOME]
            self.ship_status[ship.id][ACTION] = action
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
        if do_spawn and not me.shipyard.position in self.next_positions.values() and me.halite_amount >= constants.SHIP_COST:
            logging.info("Shipyard will spawn...")
            self.num_spawn += 1
            command_queue.append(me.shipyard.spawn())
            

        # Postprocessing
        self.postprocess()
        logging.info("Current Halite {}".format(me.halite_amount))
        # End the game
        self.game.end_turn(command_queue)
        

    