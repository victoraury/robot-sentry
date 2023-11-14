# pip3 install fastapi "uvicorn[standard]"
# uvicorn controller:app --reload

import asyncio
import contextlib
import fastapi
import time
from pydantic import BaseModel
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

class Offset(BaseModel):
    x: float
    y: float

def clamp(min: float, value: float, max: float):
    if value < min:
        return min
    if value > max:
        return max
    return value

class Driver:
    def __init__(self, Q, Qb, PWM, offset) -> None:
        GPIO.setup(Q, GPIO.OUT)
        GPIO.setup(Qb, GPIO.OUT)
        GPIO.setup(PWM, GPIO.OUT)

        self.Q = Q
        self.Qb = Qb
        self.PWM = GPIO.PWM(PWM, 256)
        self.offset = offset

        self.reset()
    
    def reset(self):
        GPIO.output(self.Q, GPIO.LOW)
        GPIO.output(self.Qb, GPIO.LOW)
        self.PWM.start(0)
    
    def signal(self, value):
        intensity = clamp(0, abs(value), 1)
        intensity = 0 if intensity == 0 else self.offset + (100-self.offset)*intensity*100

        if value == 0:
            GPIO.output(self.Q, GPIO.LOW)
            GPIO.output(self.Qb, GPIO.LOW)
        elif value < 0:
            GPIO.output(self.Q, GPIO.HIGH)
            GPIO.output(self.Qb, GPIO.LOW)
        else:
            GPIO.output(self.Q, GPIO.LOW)
            GPIO.output(self.Qb, GPIO.HIGH)
        self.PWM.start(int(intensity))


class Controller:
    def __init__(self, driver, Kp = 1.0, Ki = 0.0, Kd = 0.0) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_update = time.time()
        self.prev_error = 0
        self.acc_integral = 0
        self.output = 0
        self.driver = driver

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
        self.driver.signal(U)


    def reset(self):
        self.prev_update = time.time()
        self.prev_error = 0
        self.acc_integral = 0
        self.output = 0
        self.driver.reset()


async def set_interval(interval, func, *args, **kwargs):
    while True:
        func(*args, **kwargs)
        await asyncio.sleep(interval)
    
@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):

    app.state.driverX = Driver(24, 26, 32, 40)
    # app.state.driverY = Driver()

    app.state.controllerX = Controller(app.state.driverX, .6)
    # app.state.controllerY = Controller()
    
    app.state.counter = 0

    def emergency_stop():
        if app.state.counter:
            print("EMERGENCY STOP")
            app.state.controllerX.reset()
            # app.state.controllerY.reset()
        app.state.counter += 1
    
    asyncio.create_task(set_interval(.5, emergency_stop))

    yield

    app.state.controllerX.reset()
    # app.state.controllerY.reset()
    print("ROBOT OFF!")

app = fastapi.FastAPI(lifespan=lifespan)

@app.post("/")
def register_offset(offset: Offset):
    app.state.counter = 0
    return "well done"
