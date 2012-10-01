
#include "task_manager_lib/TaskScheduler.h"
#include "task_manager_lib/DynamicTask.h"
#include "task_manager_test/TaskIdle.h"

using namespace task_manager_test;

void waitabit(unsigned int bit)
{
	printf("Waiting %d bits:",bit); fflush(stdout);
	for (unsigned int i=0;i<bit;i++) {
		sleep(1);
		//printf(".");
		//fflush(stdout);
	}
	printf("\n");
}


void testTSe()
{
    ros::NodeHandle nh("~");
    boost::shared_ptr<TaskEnvironment> env(new TaskEnvironment());
	TaskParameters tp;
	printf("\n*******************\n\nTesting task scheduler functions (sequence)\n");
	printf("Loading tasks parameters\n");
	// tp.loadFromString(config);
	tp.setParameter("task_timeout",10.);
    tp.setParameter("main_task",false);

	printf("Creating tasks\n");
    boost::shared_ptr<TaskDefinition> idle(new TaskIdle(env));
    boost::shared_ptr<TaskDefinition> dtask1(new DynamicTask("./lib/libTaskTest.so",env));
	dtask1->setName("Task1");
    boost::shared_ptr<TaskDefinition> dtask2(new DynamicTask("./lib/libTaskTest.so",env));
	dtask2->setName("Task2");

	printf("Creating task scheduler\n");
	TaskScheduler ts(nh,idle, 0.5);
	ts.printTaskDirectory();
	printf("Adding tasks\n");
	ts.addTask(dtask1);
	ts.addTask(dtask2);
	ts.printTaskDirectory();
	printf("Configuring tasks\n");
	ts.configureTasks();
	printf("Launching idle task\n");
	ts.startScheduler();
	waitabit(2);
	printf("Launching test tasks in foreground\n");
	tp.setParameter("task_period",0.5);
	TaskScheduler::TaskId id1 = ts.launchTask(dtask1->getName(),tp);
	printf("Task id: %d\n",(int)id1);
	ts.waitTaskCompletion(id1,50.0);
	printf("Task completed\n");


	tp.setParameter("task_period",0.7);
	TaskScheduler::TaskId id2 = ts.launchTask(dtask2->getName(),tp);
	printf("Task id: %d\n",(int)id2);
	ts.waitTaskCompletion(id2,50.0);
	printf("Task completed\n");
	waitabit(1);
	// don't delete tasks, because the ts took responsibility for them
	printf("Destroying task scheduler\n");
}


int main(int argc, char * argv[])
{
    ros::init(argc,argv,"client");
	testTSe();

	return 0;
}