import roslib; roslib.load_manifest('task_manager_lib')
from task_manager_lib.TaskClient import *
import smach
import smach_ros
import signal
import sys

from std_srvs.srv import Empty, EmptyResponse

class MissionFailed(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                outcomes=['MISSION_FAILED'])

class MissionCompleted(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                outcomes=['MISSION_COMPLETED'])

class TaskState(smach.State):
    def __init__(self,mi,tc,name,**params):
        smach.State.__init__(self, 
                outcomes=['TASK_COMPLETED','TASK_INITIALISATION_FAILED','TASK_INTERRUPTED',
                    'TASK_FAILED','TASK_TIMEOUT','MISSION_COMPLETED'])
        self.mi = mi
        self.tc = tc
        self.name = name
        self.params = params
        self.id = None

    def execute(self, userdata):
        if self.mi.is_shutdown():
            return 'MISSION_COMPLETED'
        # rospy.loginfo('Executing state '+self.name)
        try:
            self.id = self.tc.tasklist[self.name].start(**self.params)
            self.tc.waitTask(self.id)
            return 'TASK_COMPLETED'
        except TaskConditionException:
            return 'TASK_INTERRUPTED'
        except TaskException, e:
            if e.status == TaskStatus.TASK_TIMEOUT:
                return 'TASK_TIMEOUT'
            elif e.status == TaskStatus.TASK_INITIALISATION_FAILED:
                return 'TASK_INITIALISATION_FAILED'
            elif e.status == TaskStatus.TASK_INTERRUPTED or e.status == None:
                # If terminated using Ctrl+C status is None
                return 'TASK_INTERRUPTED'
            return 'TASK_FAILED'

    def request_preempt(self):
        if self.id:
            # print "Preempting task %s:%d"%(self.name,self.id)
            self.tc.stopTask(self.id)

class MissionStateMachine:
    def __init__(self,tc=None):
        self.shutdown_requested = False
        self.pseudo_states={}
        self.sm = None
        server_node = rospy.get_param("~server","/turtlesim_tasks")
        default_period = rospy.get_param("~period",0.2)
        if tc:
            self.tc = tc
        else:
            self.tc = TaskClient(server_node,default_period)
        # self.tc.verbose = 2
        self.complete_srv = rospy.Service(self.tc.server_node + "/complete_mission", Empty, self.shutdown)

    def shutdown(self, _):
        if self.sm is not None:
            self.shutdown_requested = True
            self.sm.request_preempt()
        else:
            rospy.logwarn("State Machine not running. Call run() method first.")
        return EmptyResponse()

    def is_shutdown(self):
        return self.shutdown_requested

    def createStateMachine(self):
        return smach.StateMachine(outcomes=['TASK_COMPLETED','TASK_INITIALISATION_FAILED','TASK_INTERRUPTED',
                    'TASK_FAILED','TASK_TIMEOUT','MISSION_COMPLETED'])

    def createSequence(self):
        return smach.Sequence(outcomes=['TASK_COMPLETED','TASK_INITIALISATION_FAILED','TASK_INTERRUPTED',
                    'TASK_FAILED','TASK_TIMEOUT','MISSION_COMPLETED'],
                connector_outcome='TASK_COMPLETED')

    class concurrent_outcome_cb:
        def __init__(self,mi,fg):
            self.mi = mi
            self.fg = fg
        def __call__(self,states):
            print states
            if self.mi.is_shutdown():
                return 'TASK_INTERRUPTED'
            num_complete = sum([1 for x in states.values() if x == 'TASK_COMPLETED'])
            if num_complete>=1:
                return 'TASK_COMPLETED'
            return states[self.fg]

    def createConcurrence(self,fg_state,outcome_cb=None,child_termination_cb=lambda x: True):
        # Create the sub SMACH state machine
        if not outcome_cb:
            outcome_cb = self.concurrent_outcome_cb(self,fg_state)
        return smach.Concurrence(outcomes=['TASK_COMPLETED','TASK_INITIALISATION_FAILED','TASK_INTERRUPTED',
                    'TASK_FAILED','TASK_TIMEOUT','MISSION_COMPLETED'], default_outcome='TASK_FAILED',
                    outcome_cb = outcome_cb,
                    child_termination_cb=child_termination_cb)

    class TaskEpsilon(smach.State):
        def __init__(self):
            smach.State.__init__(self, outcomes=['TASK_COMPLETED','TASK_FAILED'])
        def execute(self, userdata):
            return 'TASK_COMPLETED'

    def epsilon_task(self,label=None,transitions=None):
        if not label:
            label=self.getLabel("Epsilon")
        if transitions:
            smach.Sequence.add(label, self.TaskEpsilon(),transitions)
        else:
            smach.Sequence.add(label, self.TaskEpsilon())
        return label


    def getLabel(self,name):
        state_name = "__"+name+"_0"
        if name in self.pseudo_states:
            state_name = "__" + name + "_" + str(self.pseudo_states[name])
        else:
            self.pseudo_states[name] = 0
        self.pseudo_states[name] += 1
        return state_name

    def task(self,name,**params):
        foreground = params['foreground']  # This must be defined
        state_name = None
        if 'label' in params:
            state_name=params['label']
            del params['label']
        else:
            state_name = self.getLabel(name)
        if 'transitions' in params:
            T=params['transitions']
            del params['transitions']
        else:
            # Set default connections
            T={'TASK_COMPLETED':'TASK_COMPLETED',
            'TASK_INITIALISATION_FAILED':'TASK_INITIALISATION_FAILED',
            'TASK_INTERRUPTED':'TASK_INTERRUPTED',
            'TASK_FAILED':'TASK_FAILED',
            'TASK_TIMEOUT':'TASK_TIMEOUT',
            'MISSION_COMPLETED':'MISSION_COMPLETED'}
        smach.StateMachine.add(state_name, TaskState(self,self.tc,name,**params),T)
        return state_name

    def seq_task(self,name,**params):
        state_name = None
        params['foreground']=True
        if 'label' in params:
            state_name=params['label']
            del params['label']
        else:
            state_name = self.getLabel(name)
        if 'transitions' in params:
            T=params['transitions']
            del params['transitions']
            smach.Sequence.add(state_name, TaskState(self,self.tc,name,**params),T)
        else:
            smach.Sequence.add(state_name, TaskState(self,self.tc,name,**params))
        return state_name

    def concurrent_task(self,name,**params):
        state_name = self.getLabel(name)
        foreground = params['foreground'] # This must be defined
        if 'label' in params:
            state_name=params['label']
            del params['label']
        smach.Concurrence.add(state_name, TaskState(self,self.tc,name,**params))
        return state_name

    def run(self,sm):
        self.sm = sm
        sis = smach_ros.IntrospectionServer('mission_state_machine', self.sm, '/SM')
        sis.start()

        self.sm.execute()

        sis.stop()

