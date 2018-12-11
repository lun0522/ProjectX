from multiprocessing import Manager, Process
from threading import Thread

__all__ = ["ProcessPool", "ThreadPool"]


class _Pool(object):

    @staticmethod
    def split_index(data, num_chunk):
        chunk_size = (len(data) + num_chunk - 1) // num_chunk
        for i in range(num_chunk):
            yield i * chunk_size, (i + 1) * chunk_size

    @staticmethod
    def _execute(func, args, shared, lock, name):
        print(f"Firing {name}")
        while True:
            with lock:
                if args.empty():
                    break
                next_args = args.get()
            func(next_args, shared)
        print(f"{name} finished")

    def __init__(self, _class, num_instance, func, args, shared):
        self.lock = Manager().Lock()
        self.queue =  Manager().Queue()
        [self.queue.put(elem) for elem in args]
        self.instances = []
        for i in range(num_instance):
            instance = _class(target=_Pool._execute,
                              args=(func, self.queue, shared,
                                    self.lock, f"{_class.__name__}-{i + 1}"))
            instance.start()
            self.instances.append(instance)

    def join(self):
        [instance.join() for instance in self.instances]


class ProcessPool(_Pool):

    def __init__(self, num_process, func, args, shared):
        super().__init__(Process, num_process, func, args, shared)


class ThreadPool(_Pool):

    def __init__(self, num_thread, func, args, shared):
        super().__init__(Thread, num_thread, func, args, shared)
