from machine import Pin, ADC, PWM
from time import ticks_ms, sleep_ms
import math 
from display import Display
from rotary_irq_rp2 import RotaryIRQ
import uasyncio as asyncio
from primitives import EButton
from control import TempController
class fryerState:
    # ADC
    adc = ADC(Pin(28, mode=Pin.IN))
    lowPower = Pin(23, mode=Pin.OUT, value=0)

    # Knob LEDs
    knobLedOrange = Pin(10, Pin.OUT)
    knobLedBlue = Pin(11, Pin.OUT)

    # Knob Button
    knobButton = EButton(Pin(9, Pin.IN))

    # Board LED
    led = Pin("LED", Pin.OUT)

    # Relay
    p6 = Pin(6)
    relay = PWM(p6)

    # Beeper
    p4 = Pin(4)
    beeper = PWM(p4)

    # Knob
    knob = RotaryIRQ(pin_num_clk=7,
                pin_num_dt=8,
                min_val=int(140/5),
                max_val=int(375/5),
                reverse=False,
                range_mode=RotaryIRQ.RANGE_BOUNDED)
    rotaryEvent = asyncio.Event()

    # Display
    display = Display()

    # config values
    loopMs = 5000

    def __init__(self):
        # some pin initializastion
        Pin(26, Pin.IN)
        # self.display.setSV(int(self.knob.value())*5)
        # self.display.setPV("lo")
        self.display.off()
        self.setValueOld = int(self.knob.value() * 5)
        self.setValueNew = self.setValueOld
        # self.lowPower.high()

        self.relay.freq(1000)
        self.relay.duty_u16(0)

    def relayOn(self):
        self.relay.duty_u16(32768)
    
    def relayOff(self):
        self.relay.duty_u16(0)
    
    def beepOn(self):
        self.beeper.duty_u16(32768)
    
    def beepOff(self):
        self.beeper.duty_u16(0)

    async def beep(self):
        self.beepOn()
        await asyncio.sleep_ms(75)
        self.beepOff()

    async def alert(self):
        for c in range(3):
            await self.beep()
            await asyncio.sleep_ms(50)
    
    def off(self):
        self.beepOff()
        self.relayOff()
        self.display.off()
        self.display.setSV(int(self.knob.value())*5)
        self.display.setPV("lo")
        self.knobLedBlue.low()
        self.knobLedOrange.low()

state = fryerState()

def knobCallback():
    state.rotaryEvent.set()

state.knob.add_listener(knobCallback)

def samplesToTemp(v):
    i = 0.000036    # Current source
    # Tx = 25         # Reference temp
    # Rtx = 250000.0  # Resistance at reference tempi9i9i9
    CMax = 65535.0  # Max ADC Counts
    # alpha = .044    # delta R per degree C
    Vref = 2.5      # Reference Voltage
    Taz = -273.15   # offset to absolute 0
    # return 

    # Calculated Steinhart-Hart model coefficients (https://www.thinksrs.com/downloads/programs/therm%20calc/ntccalibrator/ntccalculator.html)
    A = 1.451371111e-3
    B = 0.6977565024e-4
    C = 6.210453074e-7
    R = Vref * (v/CMax) / i # =VRef * (I2/65535) / Current
    return 1/(A + B * math.log(R) + C * math.log(R) ** 3) + Taz


########################
# Async Functions
########################
async def ui(s: fryerState):
    while True:
        s.display.nextDigit()
        await asyncio.sleep_ms(1)

            
async def regulate(s: fryerState):
    controller = TempController()
    alerted = False
    while True:
        oversample = 0
        for counter in range(8):
            oversample += s.adc.read_u16()/8
        currentTemp = samplesToTemp(oversample)

        # Check for out of bounds reading
        if oversample < 500:
            s.relayOff()
            await s.alert()
            print ("[ERROR] Reading is too low to use. Turning off.")
            s.display.setPV("---")
            s.display.setSV("---")
            await asyncio.sleep_ms(2000)
            raise Exception("Temp out of range")
        tempInF = currentTemp * (9/5) + 32
        print("PV: {}, SV: {}, Raw Reading: {}".format(tempInF, s.setValueNew, oversample))
        if tempInF < 140:
            s.display.setPV(" lo")
        else:
            s.display.setPV(int(tempInF))
        dutyCycle = controller.getDemand(s.setValueNew, tempInF)
        if controller.inRange(s.setValueNew, tempInF):
            s.knobLedOrange.high()
            s.knobLedBlue.low()
        else :
            s.knobLedBlue.high()
            s.knobLedOrange.low()

        if not alerted and tempInF >= s.setValueNew:
            await s.alert()
            alerted = True
        
        onTime = int(dutyCycle * s.loopMs)
        if onTime < 500:
            onTime = 0
        
        if onTime > s.loopMs - 500:
            onTime = s.loopMs
        
        if onTime > 0:
            s.relayOn()
            await asyncio.sleep_ms(onTime)
        
        if dutyCycle != 1.0:
            s.relayOff()

        await asyncio.sleep_ms(s.loopMs - onTime)


async def knobHandler(s: fryerState):
    while True:
        await s.rotaryEvent.wait()
        s.setValueNew = int(s.knob.value() * 5)

        if s.setValueNew != s.setValueOld:
            s.setValueOld = s.setValueNew
            s.display.setSV(s.setValueNew)

        s.rotaryEvent.clear()

########################
# /Async Functions
########################

# https://yiweimao.github.io/blog/async_microcontroller/
def set_global_exception(s: fryerState):
    """Allow for exception handling in event loop."""
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        s.off()
        asyncio.new_event_loop()
        s.beepOn()
        sleep_ms(200)
        s.beepOff()

        # sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

async def main(s: fryerState):
    set_global_exception(state) # Debug aid

    # we are either on or off. We start in the off state
    while True:
        # system is off
        await s.knobButton.press.wait()
        print("Powering up...")
        s.knobButton.press.clear()
        await s.beep()

        # system is on
        # insert coros into queue!
        uiTask = asyncio.create_task(ui(state))
        knobTask = asyncio.create_task(knobHandler(state))
        regulateTask = asyncio.create_task(regulate(state))

        # Turn off when we get a long press
        await s.knobButton.long.wait()
        print("Powering Down...")
        s.off()
        uiTask.cancel()
        knobTask.cancel()
        regulateTask.cancel()
        await s.beep()
        await asyncio.sleep_ms(2000)
        s.knobButton.long.clear()
        s.knobButton.press.clear()



########################
# Startup
########################

# display fw version
state.display.setPV("---")
state.display.setSV("002")
startTime = ticks_ms()
state.beepOn()
sleep_ms(100)
state.beepOff()

while ticks_ms() - startTime < 2000:
    state.display.nextDigit()
    sleep_ms(1)

state.off()

# Run the Event Loop
try:
    asyncio.run(main(state))
except KeyboardInterrupt: 
    state.off()
    print("Keyboard Interrupted")
except asyncio.TimeoutError: 
    print("Timed out")
finally:
    asyncio.new_event_loop()  # Clear retained state
