import time

class TimerError(Exception):
    """A custom exception used to report errors in use of Timer class"""

class Timer:
    def __init__(self):
        self._start_time = None
        self._target_time = None

    def start(self, time_in_sec):
        self._target_time = time_in_sec
        """Start a new timer"""
        if self._start_time is not None:
            raise TimerError(f"Timer is running. Use .stop() to stop it")
        self._start_time = time.perf_counter()

    def get_time(self):
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")
        elapsed_time = time.perf_counter() - self._start_time
        print(f"Elapsed time: {elapsed_time:0.4f} seconds")
        return elapsed_time


    def is_finihed(self):
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")
        if self._target_time is None:
            raise TimerError(f"Target time is not set. Use start(time_in_sec): to start it")
        elapsed_time = time.perf_counter() - self._start_time
        if elapsed_time >= self._target_time:
            return True
        else:
            return False

    def stop(self):
        """Stop the timer, and report the elapsed time"""
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")

        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None
        self._target_time = None
        print(f"Elapsed time: {elapsed_time:0.4f} seconds")