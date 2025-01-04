from pathlib import Path
from typing import List, Optional
from collections.abc import Iterable
import time
from functools import wraps
import logging

def get_files(directory: str, extension: Optional[List[str]] = None,exclude_dirs: Optional[List[str]] = None) -> List[Path]:
    """
    获取指定目录下的文件，支持指定类型与排除指定目录
    """
    path_obj = Path(directory)
    file_paths = list(path_obj.rglob('*'))
    
    file_paths = [f for f in file_paths if f.is_file()]
    
    if isinstance(extension, Iterable):
        extension = {ext.lower() for ext in extension}
        file_paths = [f for f in file_paths if f.suffix.lower() in extension]
        
    if isinstance(exclude_dirs, Iterable):
        file_paths = [
        file_path for file_path in file_paths 
        if not any(exclude_dir in file_path.parts for exclude_dir in exclude_dirs)
    ]  
    return file_paths




def timing_decorator(func):
    """
    用于测量和打印函数运行时间的装饰器。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"函数 {func.__name__} 运行耗时: {elapsed_time:.4f} 秒")
        return result
    return wrapper

    
def log_decorator(logger=logging,print_in: bool=True):
    """
    用于记录追踪函数运行情况的装饰器。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_str = f"{func.__name__} 开始执行"
            logger.info(start_str)
            if print_in:
                print(start_str)
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            end_str = f"{func.__name__} 执行完毕 ,用时{elapsed_time:.4f} s"
            logger.info(end_str)
            if print_in:
                print(end_str)
            return result
        return wrapper
    return decorator

def retry_decorator(max_retries=3, delay=1, backoff=2, exceptions=(Exception,),logger=logging,print_in: bool=True):
    """
    用于异常自动重试函数的装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    error_str = f"第 {retries + 1} 次重试。异常：{e}"
                    logger.error(error_str)
                    if print_in:
                        print(error_str)
                    retries += 1
                    if retries >= max_retries:
                        raise Exception('{func.__name__} 执行异常')
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator



@log_decorator()
@retry_decorator()
def example_function():
    import random
    # if random.random() < 0.8:
    raise ValueError("Random error")
    time.sleep(0.5)
    # else:
    #     print("Function executed successfully")

if __name__ == "__main__":
    example_function()
