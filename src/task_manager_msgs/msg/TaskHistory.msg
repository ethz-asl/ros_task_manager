uint8 TASK_NEWBORN = 0 
uint8 TASK_CONFIGURED = 1
uint8 TASK_INITIALISED = 2
uint8 TASK_RUNNING = 3
uint8 TASK_COMPLETED = 4
uint8 TASK_TERMINATED = 5
uint8 TASK_INTERRUPTED = 6
uint8 TASK_FAILED = 7
uint8 TASK_TIMEOUT = 8
uint8 TASK_CONFIGURATION_FAILED = 9
uint8 TASK_INITIALISATION_FAILED = 10

uint8 TASK_COND_1 = 11
uint8 TASK_COND_2 = 12
uint8 TASK_COND_3 = 13
uint8 TASK_COND_4 = 14

uint32 tid
string name
time start_time
time end_time
TaskParameter[] parameters
uint8 status
