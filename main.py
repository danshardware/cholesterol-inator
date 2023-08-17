from machine import Pin, ADC
from time import ticks_ms
from display import Display
from rotary_irq_rp2 import RotaryIRQ
import uasyncio as asyncio

class fryerState:
    # ADC
    adc = ADC(Pin(28, mode=Pin.IN))
    lowPower = Pin(23, mode=Pin.OUT, value=0)

    # Knob
    knobLedOrange = Pin(10, Pin.OUT)
    knobLedBlue = Pin(11, Pin.OUT)

    # Board LED
    led = Pin("LED", Pin.OUT)

    # Knob
    knob = RotaryIRQ(pin_num_clk=7,
                pin_num_dt=8,
                min_val=int(47),
                max_val=80,
                reverse=False,
                range_mode=RotaryIRQ.RANGE_WRAP)
    rotaryEvent = asyncio.Event()

    # Display
    display = Display()

    def __init__(self):
        # some pin initializastion
        Pin(21, Pin.IN)
        Pin(26, Pin.IN)
        Pin(17, Pin.IN)
        Pin(19, Pin.IN)
        Pin(20, Pin.IN)
        Pin(22, Pin.IN)
        Pin(16, Pin.IN)
        Pin(18, Pin.IN)
        self.display.setSV(int(self.knob.value())*5)
        self.display.setPV("lo")
        # self.display.nextDigit()
        self.display.off()
        self.setValueOld = int(self.knob.value())
        self.setValueNew = self.setValueOld
        self.lowPower.high()

state = fryerState()

def knobCallback():
    state.rotaryEvent.set()

state.knob.add_listener(knobCallback)

########################
# Async Functions
########################
async def ui(s: fryerState):
    lastCheck = ticks_ms()
    while True:
        # only sample when the display is off
        s.display.nextDigit()
        await asyncio.sleep_ms(1)
        # if s.display.isStarting() and ticks_ms() - lastCheck > 5000:
        if ticks_ms() - lastCheck > 5000:
            lastCheck = ticks_ms()
            # s.display.off()
            # s.display.ledB.low()
            await asyncio.sleep_ms(200)
            await regulate(s, 0)
            

async def regulate(s: fryerState, wait: int):
    # while True:
        # s.lowPower.high()
    await asyncio.sleep_ms(1)
    oversample = 0
    for counter in range(8):
        oversample += s.adc.read_u16()/8
    print(oversample, " ", s.setValueNew)
    # s.lowPower.low()
    if wait > 0:
        await asyncio.sleep_ms(wait)

async def knobHandler(s: fryerState):
    while True:
        await s.rotaryEvent.wait()
        s.setValueNew = int(s.knob.value())

        if s.setValueNew != s.setValueOld:
            s.setValueOld = s.setValueNew
            s.display.setSV(s.setValueNew * 5)

        s.rotaryEvent.clear()

########################
# /Async Functions
########################

# https://yiweimao.github.io/blog/async_microcontroller/
def set_global_exception():
    """Allow for exception handling in event loop."""
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        # sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

async def main():
    set_global_exception() # Debug aid

    # insert coros into queue!
    uiTask = asyncio.create_task(ui(state))
    # regulateTask = asyncio.create_task(regulate(state))
    knobTask = asyncio.create_task(knobHandler(state))

    while True: # run forever
        await asyncio.sleep_ms(1000)

# Run the Event Loop
try:
    # display.nextDigit()
    asyncio.run(main())
except KeyboardInterrupt: 
    print("Keyboard Interrupted")
except asyncio.TimeoutError: 
    print("Timed out")
finally:
    asyncio.new_event_loop()  # Clear retained state
