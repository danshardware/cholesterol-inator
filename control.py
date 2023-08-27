class TempController:
    # the status flags
    __pidRangeMin__ = 20  # Start PID loop at set temp minus this. Loop is just on after this
    __pidRangeMax__ = 5   # Stop PID and turn off heater after this number

    # PID Parameters
    P = 1.0
    I = 0.1
    D = 0.2

    __iAccumulator__ = 0.0
    __iMax__ = 0.5 # maximum for iAccumulator
    __dLast__ = [0.0, 0.0, 0.0, 0.0]

    # misc
    debug = True

    def iLimit(self, num):
        return max(min(num, self.__iMax__), self.__iMax__ * -1.0)
    
    def inRange(self, setValue, processValue):
        return processValue >= setValue - self.__pidRangeMin__ and processValue <= setValue + self.__pidRangeMax__
    
    def reset(self):
        self.__iAccumulator__ = 0.0
        self.__dLast__ = [0.0, 0.0, 0.0, 0.0]
        
    def getDemand(self, setValue, processValue):
        if processValue < setValue - self.__pidRangeMin__ :
            if self.debug:
                print("[TempController] Process Value too low")
            return 1.0
        if processValue > setValue + self.__pidRangeMax__ :
            if self.debug:
                print("[TempController] Process Value too high")
            return 0.0

        error = setValue - processValue

        # compute the I factor, and accumulate
        i = error * self.I * -1.0
        self.__iAccumulator__ = self.iLimit(i + self.__iAccumulator__)

        # compute the D factor (giggle)
        self.__dLast__.append(processValue)
        self.__dLast__.pop(0)
        diffs = [self.__dLast__[i+1]-self.__dLast__[i] for i in range(len(self.__dLast__)-1)]
        d = self.D * diffs.sum()/len(diffs)

        # P value
        p = error * self.P * -1.0

        demand =  p + self.__iAccumulator__ + d

        if demand > 1.0:
            demand = 1.0
        if demand < 0.0:
            demand = 0.0

        if self.debug:
            print("[TempController] Demand is {}, P: {}, I: {}, D: {}".format(demand, p, self.__iAccumulator__, d))

        return demand

