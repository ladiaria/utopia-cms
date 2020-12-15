from threading import Thread, Lock, local, current_thread


# create local storage
data = local()

# create global counters
counters = []


class threadsafe_iter:
    """Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """

    def __init__(self, it):
        self.it = it
        self.lock = Lock()

    def __iter__(self):
        return self

    def next(self):
        with self.lock:
            return self.it.next()


def threadsafe_generator(f):
    """A decorator that takes a generator function and makes it thread-safe.
    """
    def g(*a, **kw):
        return threadsafe_iter(f(*a, **kw))
    return g


@threadsafe_generator
def count():
    i = 0
    while True:
        i += 1
        yield i


@threadsafe_generator
def count_until():
    from string import ascii_lowercase
    for item in ascii_lowercase:
        yield item


def loop(func, n, logger=None):
    """
    Runs the given function n times in a loop.
    """
    for i in range(n):
        item = func()
        if logger:
            logger.debug("%s: %d" % (current_thread().ident, item))


def loop_until(func, logger=None):
    """ runs until stopiteration raised """
    from time import sleep
    while True:
        try:
            item = func()
            # emulate process time
            sleep(1)
            # store data processed locally
            items = getattr(data, 'items', 0)
            items += 1
            data.items = items
            if logger:
                logger.debug("%s: %s" % (current_thread().ident, item))
        except StopIteration:
            # append data processed (if any) to global results and quit.
            # this can be done because list.append is threadsafe.
            if hasattr(data, 'items'):
                counters.append(data.items)
            break


def run(f, repeats=3, nthreads=2, logger=None):
    """
    Starts multiple threads to execute the given function multiple times in
    each thread.
    """
    # create threads
    threads = [
        Thread(target=loop, args=(f, repeats, logger)) for i in range(nthreads)
    ]

    # start threads
    for t in threads:
        t.start()

    # wait for threads to finish
    for t in threads:
        t.join()


def run_until(f, nthreads=2, logger=None):
    """
    Starts multiple threads to execute the given function in each thread.
    """
    # create threads
    threads = [
        Thread(target=loop_until, args=(f, logger)) for i in range(nthreads)]

    # start threads
    for t in threads:
        t.start()

    # wait for threads to finish
    for t in threads:
        t.join()


def main(logger):
    c1 = count()
    # call c1.next 3 times in 2 different threads
    run(c1.next, logger=logger)

    # example to run c2 without timeit
    # c2 = count_until()
    # call c2.next in 2 threads until no more elements
    # run_until(c2.next)

    logger.debug(counters)


if __name__ == "__main__":
    import sys
    import logging
    from timeit import timeit
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    # measuring time
    logger.debug(timeit(
        'run_until(count_until().next, 8)',
        setup='from __main__ import run_until, count_until', number=1))
    main(logger)
