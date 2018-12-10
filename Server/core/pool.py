from multiprocessing import Manager, Process
from threading import Lock, Thread

__all__ = ["ProcessPool", "ThreadPool"]


class _Pool(object):

    @staticmethod
    def split_index(data, num_chunk):
        chunk_size = (len(data) + num_chunk - 1) // num_chunk
        for i in range(chunk_size):
            yield i * chunk_size, (i + 1) * chunk_size

    @staticmethod
    def split_data(data, num_chunk):
        for begin, end in _Pool.split_index(data, num_chunk):
            yield data[begin: end]

    @staticmethod
    def _execute(func, args, shared, lock, name):
        with lock:
            print(f"Firing {name}")
        while True:
            with lock:
                if args.empty():
                    break
                next_args = args.get()
            func(next_args, shared)
        with lock:
            print(f"{name} finished")

    def __init__(self, _class, name, num_instance, func, args, shared):
        self.lock = Lock()
        self.instances = []
        self.queue =  Manager().Queue()
        [self.queue.put(elem) for elem in args]
        for i in range(num_instance):
            instance = _class(target=_Pool._execute,
                              args=(func, self.queue, shared,
                                    self.lock, f"{name}-{i + 1}"))
            instance.start()
            self.instances.append(instance)

    def join(self):
        [instance.join() for instance in self.instances]


class ProcessPool(_Pool):

    def __init__(self, num_process, func, args, shared):
        super().__init__(Process, "Process", num_process, func, args, shared)


class ThreadPool(_Pool):

    def __init__(self, num_thread, func, args, shared):
        super().__init__(Thread, "Thread", num_thread, func, args, shared)
