# pip3 install fastapi "uvicorn[standard]"
# uvicorn controller:app --reload

import asyncio
import contextlib
import fastapi
import time
from pydantic import BaseModel
# import RPi.GPIO as GPIO

# GPIO.setwarnings(False)
# GPIO.setmode(GPIO.BOARD)

class Offset(BaseModel):
    x: float
    y: float

def clamp(min: float, value: float, max: float):
    if value < min:
        return min
    if value > max:
        return max
    return value

class Controller:
    def __init__(self, Kp = 1.0, Ki = 0.0, Kd = 0.0) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_update = time.time()
        self.prev_error = 0
        self.acc_integral = 0
        self.output = 0
    
    def _send_pwm(self, value):
        pass

    def update(self, error: float):
        now = time.time()
        timedelta = clamp(0.01, now - self.prev_update, 1)
        self.prev_update = now

        P = self.Kp * error
        I = self.Ki * self.acc_integral
        D = self.Kd * (self.prev_error + error) / timedelta

        U = P + I + D

        if abs(U) < 1:
            self.acc_integral += error * timedelta

        self.prev_error = error
        self._send_pwm(U)

    def reset(self):
        self.prev_update = time.time()
        self.prev_error = 0
        self.acc_integral = 0
        self.output = 0


async def set_interval(interval, func, *args, **kwargs):
    while True:
        func(*args, **kwargs)
        await asyncio.sleep(interval)
    
@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    app.state.controller = Controller()

    app.state.counter = 0
    def fucked():
        print(app.state.counter)
        if app.state.counter:
            print("FUCKED")
        app.state.counter += 1
    asyncio.create_task(set_interval(.5, fucked))

    yield

    print("ROBOT OFF!")

app = fastapi.FastAPI(lifespan=lifespan)

@app.post("/")
def register_offset(offset: Offset):
    app.state.counter = 0
    return "well done"
