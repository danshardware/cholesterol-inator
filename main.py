from machine import Pin
from time import sleep, sleep_ms
from display import Display
from rotary_irq_rp2 import RotaryIRQ

# Knob
knobLedOrange = Pin(10, Pin.OUT)
knobLedBlue = Pin(11, Pin.OUT)

# Board LED
led = Pin("LED", Pin.OUT)

# Knob
r = RotaryIRQ(pin_num_clk=7,
              pin_num_dt=8,
              min_val=int(47),
              max_val=80,
              reverse=False,
              range_mode=RotaryIRQ.RANGE_WRAP)

########################

########################
display = Display()
val_old = r.value()
display.setSV(int(r.value())*5)
display.setPV("lo")

while True:
    #encoder
    val_new = r.value()

    if val_old != val_new:
        val_old = val_new
        print(val_new)
        display.setSV(int(val_new) * 5)

    display.nextDigit()
    sleep_ms(1)
