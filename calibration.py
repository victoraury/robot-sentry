import RPi.GPIO as GPIO
from time import sleep

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

Q, Qb, PWM = 24, 26, 32

GPIO.setup(Q, GPIO.OUT)
GPIO.setup(Qb, GPIO.OUT)
GPIO.setup(PWM, GPIO.OUT)

Q = Q
Qb = Qb
PWM = GPIO.PWM(PWM, 400)
PWM.start(0)

GPIO.output(Q, GPIO.HIGH)
GPIO.output(Qb, GPIO.LOW)
for i in range(101):
    print(i)
    PWM.ChangeDutyCycle(100-i)
    sleep(.02)
GPIO.output(Q, GPIO.LOW)
GPIO.output(Qb, GPIO.LOW)

GPIO.cleanup()

