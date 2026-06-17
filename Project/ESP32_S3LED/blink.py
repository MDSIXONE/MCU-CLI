import machine
import _thread
import time

# ESP32-S3-DevKitC-1 板载 LED 引脚
LED_PIN = 2

led = machine.Pin(LED_PIN, machine.Pin.OUT)
running = True


def blink():
    while running:
        led.on()
        time.sleep(0.5)
        led.off()
        time.sleep(0.5)


# 在后台线程中运行闪烁，避免阻塞 REPL
_thread.start_new_thread(blink, ())
