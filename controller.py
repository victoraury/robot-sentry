# pip3 install fastapi "uvicorn[standard]"
# uvicorn controller:app --reload --host=0.0.0.0

import asyncio
import contextlib
import fastapi
import time
from pydantic import BaseModel
import RPi.GPIO as GPIO

GPIO.cleanup()
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
        self.PWM = GPIO.PWM(PWM, 400)
        self.PWM.start(0)
        self.offset = offset

        self.reset()
    
    def reset(self):
        GPIO.output(self.Q, GPIO.LOW)
        GPIO.output(self.Qb, GPIO.LOW)
        self.PWM.ChangeDutyCycle(0)
    
    def signal(self, value):
        intensity = clamp(0, abs(value) * 100, 100)

        #print("intensity", intensity, value)
        if value == 0:
            GPIO.output(self.Q, GPIO.LOW)
            GPIO.output(self.Qb, GPIO.LOW)
        elif value < 0:
            print("GOING RIGHT")
            GPIO.output(self.Q, GPIO.HIGH)
            GPIO.output(self.Qb, GPIO.LOW)
        else:
            print("GOING LEFT")
            GPIO.output(self.Q, GPIO.LOW)
            GPIO.output(self.Qb, GPIO.HIGH)
        self.PWM.ChangeDutyCycle(int(intensity))


class Controller:
    def __init__(self, driver, Kp = 1.0, Ki = 0.0, Kd = 0.0, dead = 1.0) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_update = time.time()
        self.prev_error = 0
        self.acc_integral = 0
        self.output = 0
        self.driver = driver
        self.dead = dead

    def update(self, error: float):
        now = time.time()
        timedelta = clamp(0.01, now - self.prev_update, 1)
        self.prev_update = now

        P = self.Kp * error
        I = self.Ki * self.acc_integral
        D = self.Kd * (error-self.prev_error) / timedelta
        U = P + I + D

        if abs(P) < self.dead:
            self.acc_integral += error * timedelta
        else:
            self.acc_integral = 0

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

    app.state.driverX = Driver(24, 26, 32, 20)
    app.state.driverY = Driver(29, 31, 33, 10)

    app.state.controllerX = Controller(app.state.driverX, .42, .175, .06, .25)
    app.state.controllerY = Controller(app.state.driverY, .7, .5, .04, .2)
    
    app.state.counter = 0

    def emergency_stop():
        #print("emergency stopped")
        if app.state.counter > 0:
            print("EMERGENCY STOP", time.time())
            app.state.controllerX.reset()
            app.state.controllerY.reset()
        app.state.counter += 1
    
    asyncio.create_task(set_interval(.5, emergency_stop))

    yield

    app.state.controllerX.reset()
    app.state.controllerY.reset()
    GPIO.cleanup()
    print("ROBOT OFF!")

app = fastapi.FastAPI(lifespan=lifespan)

@app.post("/")
def register_offset(offset: Offset):
    #print("offset:", offset, time.time())
    app.state.counter = 0
    app.state.controllerX.update(offset.x)
    app.state.controllerY.update(offset.y)
    return "well done"
