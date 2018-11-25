# CallMaker -- a set of tools to create a call schedule for a series of residents
# David Brandman
# November 2018

"""

The goal of this little project is to automagically generate call schedules.
Schedules are created according to valid rules of what may constitute a "legal"
call schedule. The list of doctors, and their availability, is defined in a
json file. The idea is to generate some kind of "optimal" call schedule,
according to some rules!

The program works as follows: 
    1. Load the JSON file
    2. Populate a CallSchedule object
    3. Bootstrap valid CallSchedule configurations, according to rules 
    4. Compute a score for the call schedule 
    5. Bootstrap until a schedule is generated that you like!

A Doctor object is defined by a name and a PGY year. The doctor can also
specify a set of days when they're avilable, and can then also specify days
when they're not available.

The original approach I took to this actually went through recursive trees to
find the optimal configuration. This worked for about 12-14 days, but then the
combinatorical explosion blew up and it stopped being practical. Thereafter I
switched to bootstrapping

"""

from datetime import timedelta, date
import datetime
import time
import calendar
import copy
import json
import random
from tqdm import tqdm # For the status bar, makes it very pretty
from collections import Counter


###################################################################
###################################################################

class CalendarRules:


    # PGME rule: cannot be on call more than 7 days per 28 days

    @staticmethod
    def IsSameDoctorOnCallMoreThanSevenDays(callSchedule):

        if len(callSchedule.onCall) == 0:
            return 0

        names = [n.name for n in callSchedule.onCall]

        tabulatedList = Counter(names)
        nCalls = [n for _,n in tabulatedList.items()]

        for ii in nCalls:
           if ii > 70:
               return 1

        return 0

    # PGME rule: Cannot have a doctor on call two days in a row
    # We loop through each assigned day, and then just check if the
    # assigned doctors are the same.

    @staticmethod
    def IsSameDoctorAssignedTwoConsectiveDays(callSchedule):

        for i in range(len(callSchedule.onCall)-1):
            if callSchedule.onCall[i] is not None and callSchedule.onCall[i+1] is not None:
                if callSchedule.onCall[i] == callSchedule.onCall[i+1]:
                    return 1
        return 0

    # PGME Rule: Cannot have a doctor on two subsequent weekends

    @staticmethod
    def IsSameDoctorAssignedTwoConsecutiveWeekends(callSchedule):

        # def IsWeekend(value):
        #     return value == 5 or value == 6 #Monday = 0, Sunday = 6
        # So the approach is to go through each callDays and find all of the weekends
        # Next, check to see if someone is on call the subsequent weekend

        if len(callSchedule.onCall) == 0:
            return 0

        saturdayCallDays = [callSchedule.dateRange.index(d) for d in callSchedule.dateRange if d.weekday() == 5]
        sundayCallDays   = [callSchedule.dateRange.index(d) for d in callSchedule.dateRange if d.weekday() == 6]

        onCallSaturday = [callSchedule.onCall[d] for d in saturdayCallDays]
        onCallSunday   = [callSchedule.onCall[d] for d in sundayCallDays]


        for ii in range(len(onCallSaturday)-1):
            if onCallSaturday[ii] == onCallSaturday[ ii+1 ]:
                return 1
            if ii+1 < len(onCallSunday) and onCallSaturday[ ii ] == onCallSunday[ ii+1 ]:
                return 1

        for ii in range(len(onCallSunday)-1):
            if onCallSunday[ ii ] == onCallSunday[ ii+1 ]:
                return 1
            if ii+1 < len(onCallSaturday) and onCallSunday[ ii ] == onCallSaturday[ ii+1 ]:
                return 1


        

        # weekendDays = saturdayCallDays + sundayCallDays

        # for ii in weekendDays:
        #     for jj in weekendDays:
        #         if ii != jj and callSchedule.onCall[ii] is not None and callSchedule.onCall[jj] is not None:
        #             if callSchedule.onCall[ii] == callSchedule.onCall[jj]:
        #                 return 1


#         for sat in saturdayCallDays:
#             for sun in sundayCallDays:
#                 if callSchedule.onCall[sat] is not None and callSchedule.onCall[sun] is not None:
#                     if callSchedule.onCall[sat] == callSchedule.onCall[sun]:
#                         return 1

        return 0 

###################################################################
###################################################################

class CalendarScore:


    # Score: Compute the total PGY year of the current calendar setup

    @staticmethod
    def ScoreSumOfPGY(callSchedule):
        x = [d.year*2 for d in callSchedule.onCall]
        return sum(x)

    # Score: Compute a score that tries to space out resident calls.
    # For each doctor's call schedule, compute the number of days
    # between call shifts, x. Then, add 4 - x to the score. This
    # adds a "memory" component to the call schedule!
    # Since we're not using numpy, there's a little tomfoolery going on here.
    # The diff = [j-i ...] code is computing the difference in days
    # between contiguous call shifts. 

    @staticmethod
    def ScoreMaximizeDistanceBetweenCalls(callSchedule):
        runningScore = 0
        for d in callSchedule.doctors:
            x = callSchedule.GetCallDaysForDoctor(d)
            if x is not None:
                diff = [j-i for i, j in zip(x[:-1], x[1:])]
                daysBetweenCalls = [max(4-y.days,0) for y in diff]
                runningScore += sum(daysBetweenCalls)

        return runningScore

###################################################################
###################################################################

# Call schedule contains a valid date range, some doctors, and then can read a jsonStructure
# Contains a onCall field, which is an array of doctors

class CallSchedule:

    def __init__(self, startDate = None, endDate = None,  doctors = [], jsonStructure = None):

        self.dateRange  = []
        self.doctors 	= doctors
        self.onCall     = []

        self.SetDateRange(startDate, endDate)
        self.ParseJsonStructure(jsonStructure)

    def SetDateRange(self, startDate, endDate):
        if startDate is None or endDate is None: return

        dateDelta = endDate - startDate
        dateRange = [startDate + timedelta(d) for d in range(dateDelta.days+1)]
        
        self.dateRange  = dateRange	
        self.onCall     = [None] * (dateDelta.days+1)	

    def ParseJsonStructure(self,jsonStructure):
        if jsonStructure is None: return

        startDate = datetime.datetime.strptime(jsonStructure['Start-Date'], "%Y.%m.%d").date()
        endDate   = datetime.datetime.strptime(jsonStructure['End-Date'],   "%Y.%m.%d").date()

        self.SetDateRange(startDate, endDate)

        for d in jsonStructure['Doctors']:
            self.doctors.append(Doctor(jsonStructure=d))

    # The main function: is the current CallSchedule legal? Calls the rules
    def IsLegal(self):

        cond1 = CalendarRules.IsSameDoctorAssignedTwoConsectiveDays(self)
        cond2 = CalendarRules.IsSameDoctorAssignedTwoConsecutiveWeekends(self)
        cond3 = CalendarRules.IsSameDoctorOnCallMoreThanSevenDays(self)

        return not (cond1 or cond2 or cond3)

    # Every calendar has a score! Compute it
    def ComputeScore(self):
        s    = []
        s.append(CalendarScore.ScoreMaximizeDistanceBetweenCalls(self))
        s.append(CalendarScore.ScoreSumOfPGY(self))

        return sum(s)
   
    # Display the result of the CallSchedule
    def Display(self):

        for d in self.doctors:
            nCalls = len(self.GetCallDaysForDoctor(d))
            nPossibleCalls = len([e for e in self.dateRange if e in d.dateRange])
            print d.name , "Calls : " ,nCalls, ", Possible: ", nPossibleCalls

        ind = 0
        for d in self.dateRange:
            name = "Undefined" if self.onCall[ind] is None else self.onCall[ind].name
            print calendar.day_name[d.weekday()], d , name
            ind+=1



    def GetDoctorsAvailableOnDate(self, theDate = None):
        if theDate is None or self.doctors is None: return

        return [d for d in self.doctors if theDate in d.dateRange]

    # Look into the currently assigned call days, and return the first
    # day that isn't assigned

    def GetNextUnassignedCallDay(self):
        ind = 0
        for d in self.dateRange:
            if self.onCall[ind] is None:
                    return d, ind
            ind+=1

        return None, None

    def GetCallDaysForDoctor(self, theDoctor):
        return [self.dateRange[i] for i, x in enumerate(self.onCall) if x == theDoctor]




    # See the preface notes for explanation of what's happening here

    def BootstrapCallSchedule(self):

        bestCalendar = None
        bestScore = float('inf')

        nBootstraps = 100

        for ii in tqdm(range(nBootstraps)):
            while True: 
                ind = 0
                for theDate in self.dateRange:
                    availableDoctors = self.GetDoctorsAvailableOnDate(theDate)
                    randomDoctor = availableDoctors[random.randint(0,len(availableDoctors)-1)]
                    self.onCall[ind] = randomDoctor
                    ind = ind + 1

                if self.IsLegal():
                    break

            myScore = self.ComputeScore()
            if myScore < bestScore:
                bestScore = myScore
                bestCalendar = copy.deepcopy(self)


        return bestCalendar




    def CreateCallSchedule(self):

        localScope = {'lowestScore': float('inf'), 'bestCalendar': None}

        def ScheduleTree(self):

            dayToAssign, dayIndex = self.GetNextUnassignedCallDay()
            if dayToAssign is not None:
                availableDoctors = self.GetDoctorsAvailableOnDate(dayToAssign)

                for currentDoctor in availableDoctors:
                    self.onCall[dayIndex] = currentDoctor
                    if self.IsLegal():
                        ScheduleTree(self)
                    self.onCall[dayIndex] = None

            else:
                myScore = self.ComputeScore() 
                if myScore < localScope['lowestScore']:
                    #print "Score: " , myScore , "Lowest: " , localScope['lowestScore'] 
                    #self.Display()
                    localScope['lowestScore'] = myScore
                    localScope['bestCalendar'] = copy.deepcopy(self)

        ScheduleTree(self)

        #localScope['bestCalendar'].Display()
        #print "Lowest: " , localScope['lowestScore'] 
        return localScope['bestCalendar']


###################################################################
###################################################################
"""
A doctor has a name, a PGY year, some available and then unavailable
dates for being on call
"""
class Doctor:

    def __init__(self, name=None, year=None, jsonStructure=None):

        self.name      = name
        self.year      = year
        self.dateRange = []

        self.ParseJsonStructure(jsonStructure)

    # Convert the JSON information to available and unavailable dates
    def ParseJsonStructure(self,jsonStructure):
        if jsonStructure is None: return

        self.name = jsonStructure['Name']
        self.year = jsonStructure['Year']

        # Let's convert the json format to the datetime format used by this application
        for startStopDates in jsonStructure['Available']:
            startDate = datetime.datetime.strptime(startStopDates['Start-Date'], "%Y.%m.%d").date()
            endDate   = datetime.datetime.strptime(startStopDates['End-Date'],   "%Y.%m.%d").date()

            self.AddAvailableDates(startDate, endDate)

        for startStopDates in jsonStructure['Unavailable']:
            startDate = datetime.datetime.strptime(startStopDates['Start-Date'], "%Y.%m.%d").date()
            endDate   = datetime.datetime.strptime(startStopDates['End-Date'],   "%Y.%m.%d").date()

            self.RemoveAvailableDates(startDate, endDate)
    
    # Available dates are entered within date ranges
    def AddAvailableDates(self, startDate, endDate):

        # Make sure we have some valid data!
        if startDate is None or endDate is None: return
        if startDate > endDate: return

        dateDelta = endDate - startDate 
        dateRange = [startDate + timedelta(d) for d in range(dateDelta.days+1)]
        self.dateRange.extend(dateRange)

    # Unavailable dates are entered within date ranges
    # This function removes dates from within the unavailable range
    def RemoveAvailableDates(self, startDate, endDate):

        if startDate is None or endDate is None: return
        if startDate > endDate: return

        # Remove dates within a date range
        dateDelta = endDate - startDate 
        dateRange = [startDate + timedelta(d) for d in range(dateDelta.days+1)]
        for d in dateRange:
            if d in self.dateRange:
                self.dateRange.remove(d)

    # Definition of equivalent for a doctor: same name and PGY year
    def __eq__(self, other): 
        return self.name == other.name and self.year == other.year


    # Printing a doctor for debugging purposes
    def __str__(self): 
        nDays = 0 if self.dateRange is None else len(self.dateRange)
        name  = "Undefined" if self.name is None else self.name
        year  = -1 if self.year is None else self.year
        return "Doctor: %s, PGY: %d, Available Days: %d" % (name, year, nDays)

#####################################################

if __name__ == "__main__":

    # Load the configuration file
    with open('callSheet.json') as f:
        data = json.load(f)

    c = CallSchedule(jsonStructure=data)

    t = time.time()
    # d = c.CreateCallSchedule()
    d = c.BootstrapCallSchedule()
    d.Display()
    print "Elapsed Time: %.2f seconds"  % ( time.time() - t)

