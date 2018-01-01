log_file = 'PATH_TO_LOG_FILE/multi_log_test.log'

import logging
import logging.handlers
import numpy as np
import time
import multiprocessing

# Adapted from
# https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes
# with the help of
# https://stackoverflow.com/questions/48045978/how-to-log-to-single-file-with-multiprocessing-pool-apply-async

def listener_configurer():
    root = logging.getLogger()
    h = logging.FileHandler(log_file)
    f = logging.Formatter('%(asctime)s %(message)s')
    h.setFormatter(f)
    root.addHandler(h)


def listener_process(queue, configurer):
    configurer()
    while True:
        try:
            record = queue.get()
            if record is None:  # We send this as a sentinel to tell the listener to quit.
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)  # No level or filter logic applied - just do it!
        except Exception:
            import sys, traceback
            print('Whoops! Problem:', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


def task_worker_configurer(queue):
    root = logging.getLogger()
    #if not len(root.handlers):
    h = logging.handlers.QueueHandler(queue)
    root.addHandler(h)
    # send all messages, for demo; no other level or filter logic applied.
    root.setLevel(logging.DEBUG)


def task_function(sleep_time, task_name, queue, configurer):
    name = multiprocessing.current_process().name
    configurer(queue)
    start_message = 'Worker {} has started task {} and will now sleep for {}s'.format(name, task_name, sleep_time)
    logging.info(start_message)
    time.sleep(sleep_time)
    success_message = 'Worker {} has finished  task {} of sleeping for {}s'.format(name, task_name, sleep_time)
    logging.info(success_message)

    
def main():
    start_time = time.time()
    queue = multiprocessing.Manager().Queue(-1)
    listener = multiprocessing.Process(target=listener_process,
                                       args=(queue, listener_configurer))
    listener.start()
    pool = multiprocessing.Pool(processes=6, maxtasksperchild=1)
    # I need maxtasksperchild=1 to destroy / clean up each worker after its task completion.
    # I do this because without it, each time a given worker picked up a new task, the number
    # of duplicate messages for each logging event incremented by one.
    job_list = [np.random.randint(8,10) for i in range(6)]
    single_thread_time = np.sum(job_list)
    for i, sleep_time in enumerate(job_list):
        name = str(i)
        pool.apply_async(task_function,
                         args=(sleep_time, name, queue, task_worker_configurer))
    pool.close()
    pool.join()
    queue.put_nowait(None)
    end_time = time.time()
    print("sum of task lengths is {}s, but script execution time was {}s".format(
        single_thread_time,
        (end_time - start_time)
    ))
    listener.join()


if __name__ == "__main__":
    main()
