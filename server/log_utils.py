import time
import functools

def log_performance_decorator(log_func):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
            log_func(f"{timestamp} - Function {func.__name__} executed in {execution_time:.4f} seconds")
            return result
        return wrapper
    return decorator

def log_performance_metric(message=''):
    with open("performance_log.txt", "a") as file:
        file.write(message + "\n")

