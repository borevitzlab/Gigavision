import gphoto2cffi as gp
from memory_profiler import profile
import time
import sys
import gc
gc.set_debug(gc.DEBUG_UNCOLLECTABLE)
camera = gp.list_cameras()[0]
@profile
def capture():
    a = camera.capture()
    del a
    return True


try:
    while capture():
        print(gc.get_count())
        gc.collect()
except KeyboardInterrupt:
    sys.exit(0)