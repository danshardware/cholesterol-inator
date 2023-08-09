# Display driver for the 7-segment displays
from machine import Pin

MAX_DIGITS = 0x3 # number of digits per display

clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

""" 
  A ->>  ---
        |   |  
  F     |   |  B
  G ->>  ---
        |   |  
  E     |   |  C
  D ->>  --- .  <<- P

  A -> 1, B -> 2, C -> 4, D -> 8
  E -> 16, F -> 32, G -> 64, P -> 128
 """
MAX_DIGITS = 0x3 # number of digits per display

clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
def rjust(s: str, maxLen: int, pad: str):
    if len(s) >= maxLen:
        return s[:maxLen]
    
    return pad * (maxLen - len(s)) + s

characterLUT = {
    " ": 0x0,
    "0": 0x3f,
    "1": 0x06,
    "2": 0x5b,
    "3": 0x4f,
    "4": 0x66,
    "5": 0x6d,
    "6": 0x7d,
    "7": 0x07,
    "8": 0x7f,
    "9": 0x6f,
    "a": 0x0,
    "b": 0x0,
    "c": 0x0,
    "d": 0x0,
    "e": 0x0,
    "f": 0x0,
    "l": 0x30,
    "o": 0b01011100,
}

# OMG, this is inefficient
class Display:
    __SV = "  "
    __PV = "  "
    blinkPeriod = 0x0A
    __blinkCounter = 0x0
    blinking = False

    DISPLAY_SV = False # Small display, CK
    DISPLAY_PV = True # Large Display, CA
    __stateDisplay = DISPLAY_SV
    __stateDigit = 0

    def __init__(self):
        # Setup the pins to not output anything
        self.ledA = Pin(21, Pin.IN)
        self.ledB = Pin(26, Pin.IN)
        self.ledC = Pin(17, Pin.IN)
        self.ledD = Pin(19, Pin.IN)
        self.ledE = Pin(20, Pin.IN)
        self.ledF = Pin(22, Pin.IN)
        self.ledG = Pin(16, Pin.IN)
        self.ledP = Pin(18, Pin.IN)
        self.ledSegments = [self.ledA, self.ledB, self.ledC, self.ledD, self.ledE, self.ledF, self.ledG, self.ledP]

        # Digits
        self.ledD0 = Pin(13, Pin.OUT, value=1)
        self.ledD1 = Pin(14, Pin.OUT, value=1)
        self.ledD2 = Pin(15, Pin.OUT, value=1)
        self.ledDE = Pin(12, Pin.OUT, value=0) # disables the common pins
        self.ledDigits = [self.ledD0, self.ledD1, self.ledD2]
        print("Display initialized")

    def __getDigit(self, char):
        index = char[0]
        if index in characterLUT:
            return characterLUT[index]
        
        return 0x0
    
    def nextDigit(self):
        # advance to the next digit
        self.__stateDigit += int(1)
        if self.__stateDigit >= MAX_DIGITS:
            self.__stateDigit = 0
            self.__stateDisplay = not self.__stateDisplay
        
        if self.__stateDisplay == self.DISPLAY_SV:
            bitmap = self.__getDigit(self.__SV[self.__stateDigit])
            # bug out if the digit is blank
            if bitmap == 0:
                self.ledDE.low()
                return
            
            # Enable the display
            self.ledDE.high()
            # Common Cathode display
            # set the digits
            for idx, digit in enumerate(self.ledDigits):
                if idx == self.__stateDigit:
                    digit.low()
                else:
                    digit.high()
                # if idx == self.__stateDigit:
                #     print("Writing digit {}".format(idx))
            
            # Lookup the digit
            # print("stateDigit - {}, SV - _{}_".format(self.__stateDigit, self.__SV))
            counter = 0
            calcOut = []
            for segment in self.ledSegments:
                value = 1 if bitmap & (1 << counter) > 0 else 0
                pinState = Pin.OUT if value == 1 else Pin.IN
                pinPull = None if value == 1 else Pin.PULL_DOWN
                pinPull= None
                # pinState = Pin.OUT
                calcOut.append(pinState)
                segment.init(mode=pinState, value=value, pull=pinPull)
                counter += 1
        else:
            bitmap = self.__getDigit(self.__PV[self.__stateDigit])
            if bitmap == 0:
                self.ledDE.low()
                return
            
            # Enable the display
            self.ledDE.high()

            for idx, digit in enumerate(self.ledDigits):
                if idx == self.__stateDigit:
                    digit.high()
                else:
                    digit.low()
            counter = 0
            for segment in self.ledSegments:
                value = 0 if bitmap & (1 << counter) > 0 else 1
                pinState = Pin.OUT if value == 0 else Pin.IN
                pinPull = None if value == 1 else Pin.PULL_UP
                pinPull= None
                segment.init(mode=pinState, value=value, pull=pinPull)
                counter += 1
            
    def off(self):
        self.ledDE.low()
    
    def setSV(self, value : str | int):
        # ensure the value has 3 or fewer characters, or is less than 999
        if type(value) == int:
            self.__SV = rjust(str(clamp(value, 0, 999)),3, " ")
            return
        
        self.__SV =  rjust(str(value), 3, " ")
    
    def setPV(self, value : str | int):
        # ensure the value has 3 or fewer characters, or is less than 999
        if type(value) == int:
            self.__PV = rjust(str(clamp(value, 0, 999)),3, " ")
            return
        
        self.__PV =  rjust(str(value), 3, " ")

    # def __mystring
