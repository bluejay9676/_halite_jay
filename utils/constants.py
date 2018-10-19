



## Unit constants (Each ship has a corresponding info stored in ship_dict)
UNIT_INFO = 'unit_info'
STATUS = 'status'

# States
DEFAULT_STATE = 'default'
ACTION_STATE = 'action'
RUN_STATE = 'run'

# Dropoff constants
DROPOFF = 'dropoff'
DROPOFF_LOCATION = 'dropoff_location'
NUM_WORKERS = 'NUM_WORKERS'

# Guard constants
GUARD = 'guard'
GUARD_POINT = 'guard_point'
# DEFENDING = 'defending'
# PATROLING = 'patroling'

# Worker constants
WORKER = 'worker'
DELOAD_POINT = 'deload_point'
DELOAD_SHIP = 'deload_ship'
RISK_TAKER = 'risk_taker'
# EXPLORING = 'exploring'
# RETURNING = 'returning'

# Offense constants
OFFENSE = 'offense'
OFFENSE_POINT = 'offense_point'
# SEARCHING = 'searching'
# CHARGING = 'charging'

## Unit format
# Guard
DEFAULT_GUARD = {
    UNIT_INFO : GUARD,
    STATUS : DEFAULT_STATE,
    GUARD_POINT : None
}

DEFAULT_WORKER = {
    UNIT_INFO : WORKER,
    STATUS : DEFAULT_STATE,
    DELOAD_POINT : None,
    DELOAD_SHIP : None,
    RISK_TAKER : False
}

DEFAULT_OFFENSE = {
    UNIT_INFO : OFFENSE,
    STATUS : DEFAULT_STATE,
    OFFENSE_POINT : None,
}

DEFAULT_DROPOFF = {
    UNIT_INFO : DROPOFF,
    STATUS : DEFAULT_STATE,
    DROPOFF_LOCATION : None,
    NUM_WORKERS : 0
}

