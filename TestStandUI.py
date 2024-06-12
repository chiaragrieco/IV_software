#usability edits: Amina Li, UCSB 2022
#usability edits: Sebastian Carron, CLU 2024

from PyQt4 import QtCore as core, QtGui as gui
from interface.mainWindow import Ui_MainWindow
import sys
import os
import time
import numpy

from Keithley2410 import SourceMeterServer

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg    as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

#DEFAULT RUN SETTINGS
VOLTSTEP = 5               # Bias voltage step size
VOLTSTOP = 800             # Bias voltage stop point, max value reached
TIMESTEP = 1               # Interval in seconds between voltage steps

# Other globals
TIMERINTERVAL     = 50     # Interval in milliseconds between timer_event calls while the UI is running
DISPLAY_PRECISION = 6      # Number of decimal points to use on displays

MAX_CURRENT = 1.0e-3

KEITHLEY_COM = 6

MEAS_ACTUAL_MODIFIER = 0.8

t = time.localtime()

f = "IVdata_{y}-{m}-{d}_{h}-{n}-{s}.txt".format(y=t[0],m=t[1],d=t[2],h=t[3],n=t[4],s=t[5])

dpath = ""

class ivServer(object):
        def __init__(self,port):
                self.s = SourceMeterServer(port)
                #self.s.reset()
                self.s.sense_off_all()
                self.s.sense_on("CURR")
                self.s.sense_on("VOLT")                                                                                                                                                                                                                                                                                                                                                                 
                self.s.sense_current_prot(1.05e-3); print('I cpl',self.s.sense_current_prot())
                self.s.sense_current_range(1.05e-3); print('I rng',self.s.sense_current_range())
                self.s.source_mode('v')
                self.s.output_on()
                
                self.source_voltage_range = None
                self.set_source_voltage_range(21); print('v',self.s.source_voltage_range())
                
        def set_source_voltage_range(self,setto):
                if self.source_voltage_range is None:
                        self.s.source_voltage_range(setto)
                        self.source_voltage_range = self.s.source_voltage_range()
                        print("SOURCE_VOLTAGE_RANGE \t\tFirst range set to "+str(self.source_voltage_range))
                elif setto != self.source_voltage_range:
                        self.s.source_voltage_range(setto)
                        self.source_voltage_range = self.s.source_voltage_range()
                        print("SOURCE_VOLTAGE_RANGE \t\tSet range to "+str(self.source_voltage_range))
                        
        def meas(self):
                self.s.meas()
                v,a=self.s.read().replace(',','\n').splitlines()[:2]
                return float(v),float(a)
        def setv(self,v):
                if v>21:
                        self.set_source_voltage_range(1100)
                else:
                        self.set_source_voltage_range(21)


                print('v range',self.s.source_voltage_range())
                
                        
                self.s.source_voltage_level(v)

                print('I cpl',self.s.sense_current_prot())
                print('I rng',self.s.sense_current_range())
                
        def close(self):   #steps voltage down to 0 and turns output off before closing connection
                V,I = self.meas()
                while (V > 5):
                        V = V-5
                        self.s.source_voltage_level(V)
                        time.sleep(0.5)
                self.s.source_voltage_level(0)
                self.s.output_off()
                self.s.close()



def checkv(voltage):
        if voltage < 0:return 0
        if voltage > 1100:return 1100
        return voltage

ran = lambda:random.random() - 0.5

class mainDesigner(gui.QMainWindow,Ui_MainWindow):
        def __init__(self):
                super(mainDesigner,self).__init__(None)
                self.setupUi(self,VOLTSTEP,VOLTSTOP,TIMESTEP)

                self.lastTime = None
                self.measurementInterval = None; self.measurementTimer = 0.0
                self.plotRefreshInterval = None; self.plotRefreshTimer = 0.0

                self.autoStepInterval = None; self.autoStepTimer = None
                self.autoStep = False
                self.autoStepMode = None
                self.autoStepMaxCurrent = None
                self.autoStepVoltageStop = None

                self.biasVoltage = 0

                self.firstVoltageChangedIndex = 0
                self.recentVoltageChangedIndex = 0
                self.firstMeasurementTime = None
                self.data = [[],[],[],[]]

                self.s = ivServer(KEITHLEY_COM)

                self.rig()
                self.start()

        def start(self):
                self.setWindowTitle("Test Stand User Interface")
                self.timer = core.QTimer(self)               # Create timer object
                self.timer.setInterval(TIMERINTERVAL)        # Set timer interval to global TIMERINTERVAL, defined at the top of this file
                self.timer.timeout.connect(self.timer_event) # Connect timer to the timer_event function
                self.timer.start()                           # Start the timer

        def updateAutoStepInterval(self,*args,**kwargs):
                self.autoStepInterval = self.sbAutoStepInterval.value()
        def updateAutoStepVoltageStop(self,*args,**kwargs):
                self.autoStepVoltageStop = self.sbAutoVoltageStop.value()
        def updateAutoStepMaxCurrent(self,*args,**kwargs):
                if self.cbAutoMaxCurrent.isChecked():
                        self.autoStepMaxCurrent = self.sbAutoMaxCurrent.value()
                else:
                        self.autoStepMaxCurrent = None
                        
        def updateComplianceMaxCurrent(self,port):
                if self.btnSetSRangeCompliance.isChecked():
                        self.s2 = SourceMeterServer(port)
                        self.s2.sense_current_prot(20.05e-3); 
                        self.s2.sense_current_range(20.05e-3);
                else:
                        self.s2 = SourceMeterServer(port)
                        self.s2.sense_current_prot(1.05e-3); 
                        self.s2.sense_current_range(1.05e-3); 

#        def updateOutFileName(self):
#               if self.cbSetOutFileName.isChecked():
#                        global t
#                        t = time.localtime()
#                        global f
#                        f = "IVdata_{custom}.txt".format(custom=self.userOutFileName.toPlainText())
#                else:
#                        t = time.localtime()
#                        f = "IVdata_{y}-{m}-{d}_{h}-{n}-{s}.txt".format(y=t[0],m=t[1],d=t[2],h=t[3],n=t[4],s=t[5]) 

        def updateOutFileName(self):
                if self.cbSetOutDirectory.isChecked():
                        if self.cbSetOutFileName.isChecked():
                                global t
                                t = time.localtime()
                                global f
                                global dpath
                                t=time.localtime()
                                dpath="C:/Users/hep/Documents/IVCurves_UI_New/data/{customdir}/{y}{m}{d}".format(customdir=self.userOutDirName.toPlainText(),y=t[0],m=t[1],d=t[2])
                                f = "{customd}/{y}{m}{d}/IVdata_{customf}.txt".format(customf=self.userOutFileName.toPlainText(),customd=self.userOutDirName.toPlainText(),y=t[0],m=t[1],d=t[2])
                        else:
                                t = time.localtime()
                                dpath="C:/Users/hep/Documents/IVCurves_UI_New/data/{customdir}/{y}{m}{d}".format(customdir=self.userOutDirName.toPlainText(),y=t[0],m=t[1],d=t[2])           
                                f = "{customd}/IVdata_{y}-{m}-{d}_{h}-{n}-{s}.txt".format(customd=self.userOutDirName.toPlainText(),y=t[0],m=t[1],d=t[2],h=t[3],n=t[4],s=t[5])                         

                else:
                        if self.cbSetOutFileName.isChecked():
                                #global t
                                t = time.localtime()
                                #global f
                                f = "IVdata_{custom}.txt".format(custom=self.userOutFileName.toPlainText())
                        else:
                                t = time.localtime()
                                f = "IVdata_{y}-{m}-{d}_{h}-{n}-{s}.txt".format(y=t[0],m=t[1],d=t[2],h=t[3],n=t[4],s=t[5])

        
        def updateAutoStepMode(self,*args,**kwargs):
                self.autoStepMode = str(self.ddAutoDir.currentText())
        def updateAutoStep(self,*args,**kwargs):
                if self.cbAutoStep.isChecked():
                        self.autoStepOn()
                else:
                        self.autoStepOff()

        def autoStepOn(self):
                self.updateAutoStepInterval()
                self.updateAutoStepVoltageStop()
                self.updateAutoStepMaxCurrent()
                self.updateAutoStepMode()
                self.autoStepTimer = 0.0
                self.autoStep = True
                self.cbAutoStep.setChecked(True)

        def autoStepOff(self):
                self.autoStepTimer = None
                self.autoStep = False
                self.cbAutoStep.setChecked(False)

        def timer_event(self):
                """Runs each time the timer times out"""
                
                if self.lastTime is None:
                        self.lastTime = time.time()
                        dt = 0.0
                else:
                        newTime = time.time()
                        dt = newTime - self.lastTime
                        self.lastTime = newTime

                self.measurementTimer += dt
                if self.measurementTimer >= self.measurementInterval * MEAS_ACTUAL_MODIFIER:
                        self.measurementTimer = 0.0
                        self.doMeasurement()

                self.plotRefreshTimer += dt
                if self.plotRefreshTimer >= self.plotRefreshInterval:
                        self.plotRefreshTimer = 0.0
                        self.refreshPlots()

                if self.autoStep:

                        self.autoStepTimer += dt
                        #print(self.autoStepTimer,self.autoStepInterval)
                        if self.autoStepTimer >= self.autoStepInterval:
                                self.autoStepTimer = 0.0
                                #print(self.autoStepMode)
                                if self.autoStepMode == 'up':
                                        self.stepUp()
                                elif self.autoStepMode == 'down':
                                        self.stepDown()



        def doMeasurement(self):
                if self.firstMeasurementTime is None:
                        t = 0.0
                        self.firstMeasurementTime = time.time()
                else:
                        t = time.time() - self.firstMeasurementTime

                V,I = self.s.meas()

                self.data[0].append(t                ) # time of measurement
                self.data[1].append(self.biasVoltage ) # bias voltage of measurement
                self.data[2].append(I                ) # current measured
                self.data[3].append(V                ) # actual voltage measured
                self.lblCurrentMeasurement.setText(str(I))

                if I > MAX_CURRENT:
                        print("WARNING: CURRENT EXCEEDS MAX_CURRENT")
                        print("PERFORMING IMMEDIATE STEP DOWN")
                        self.stepDown()

                elif self.autoStep:
                        if not (self.autoStepMaxCurrent is None):
                                if I > self.autoStepMaxCurrent*1e-6:
                                        print("Current exceeds autoStepMaxCurrent")
                                        print("Ceasing autoStep")
                                        self.autoStepOff()
                

        def refreshPlots(self):
                #print("PLOTS REFRESHED!")
                if len(self.data) == 0:
                        return

                # plot all data
                self.axAll.clear()
                self.axAll.plot(self.data[1][self.firstVoltageChangedIndex:],self.data[2][self.firstVoltageChangedIndex:],'ro')
                self.fcAll.draw()

                # plot recent data
                if len(self.data[0]) > self.recentVoltageChangedIndex:
                        self.axLatest.clear()
                        self.axLatest.plot(
                                self.data[0][self.recentVoltageChangedIndex:],
                                self.data[2][self.recentVoltageChangedIndex:],
                                'ro')
                        self.fcLatest.draw()



        def rig(self):
                self.sbMeasurementInterval.valueChanged.connect(self.changeMeasurementInterval)
                self.sbPlotRefreshInterval.valueChanged.connect(self.changePlotRefreshInterval)
                self.changeMeasurementInterval()
                self.changePlotRefreshInterval()

                
                self.btnSetSRangeCompliance.clicked.connect(self.updateComplianceMaxCurrent)
                self.cbAutoStep.clicked.connect(self.updateAutoStep)
                self.cbAutoMaxCurrent.clicked.connect(self.updateAutoStepMaxCurrent)
                self.sbAutoMaxCurrent.valueChanged.connect(self.updateAutoStepMaxCurrent)
                self.sbAutoVoltageStop.valueChanged.connect(self.updateAutoStepVoltageStop)
                self.sbAutoStepInterval.valueChanged.connect(self.updateAutoStepInterval)
                self.ddAutoDir.currentIndexChanged.connect(self.updateAutoStepMode)

                self.btnSetVoltage.clicked.connect(self.setVoltage)
                self.btnStepUp.clicked.connect(self.stepUp)
                self.btnStepDown.clicked.connect(self.stepDown)
                self.sbStepSize.valueChanged.connect(self.updateStepToReadouts)
                self.updateStepToReadouts()
                self.lblBiasVoltage.setText(str(self.biasVoltage))

                self.figLatest = Figure(); self.axLatest = self.figLatest.add_subplot(111)
                self.fcLatest  = FigureCanvas(self.figLatest)
                self.tbLatest  = NavigationToolbar(self.fcLatest,self)
                self.vlGraphLatestV.addWidget(self.tbLatest)
                self.vlGraphLatestV.addWidget(self.fcLatest)

                self.figAll    = Figure(); self.axAll = self.figAll.add_subplot(111)
                self.fcAll     = FigureCanvas(self.figAll)
                self.tbAll     = NavigationToolbar(self.fcAll,self)
                self.vlGraphAllV.addWidget(self.tbAll)
                self.vlGraphAllV.addWidget(self.fcAll)

                self.cbSetOutFileName.clicked.connect(self.updateOutFileName)
                #self.cbSetOutDirectory.clicked.connect(self.updateOutDirName)


        def _changeVoltage(self,voltage):
                print("SET VOLTAGE TO {voltage}".format(voltage=voltage))
                self.s.setv(voltage)
                if self.recentVoltageChangedIndex == 0:
                        self.firstVoltageChangedIndex = len(self.data[0])
                self.recentVoltageChangedIndex = len(self.data[0])
                self.measurementTimer = 0.0

        def setVoltage(self,*args,**kwargs):
                voltage = checkv(self.sbSetVoltage.value())
                self._changeVoltage(voltage)
                self.biasVoltage = voltage
                self.lblBiasVoltage.setText(str(voltage))
                self.updateStepToReadouts()

        def stepUp(self,*args,**kwargs):
                voltage = checkv(self.biasVoltage + self.sbStepSize.value())
                self._changeVoltage(voltage)
                self.biasVoltage = voltage
                self.lblBiasVoltage.setText(str(voltage))
                self.updateStepToReadouts()

                if self.autoStep and self.autoStepMode == 'up':
                        if voltage >= self.autoStepVoltageStop:
                                print("autoStepVoltageStop reached")
                                print("stopping autoStep")
                                self.autoStepOff()


        def stepDown(self,*args,**kwargs):
                voltage = checkv(self.biasVoltage - self.sbStepSize.value())
                self._changeVoltage(voltage)
                self.biasVoltage = voltage
                self.lblBiasVoltage.setText(str(voltage))
                self.updateStepToReadouts()

                if self.autoStep and self.autoStepMode == 'down':
                        if voltage <= self.autoStepVoltageStop:
                                print("autoStepVoltageStop reached")
                                print("stopping autoStep")
                                self.autoStepOff()


        def updateStepToReadouts(self,*args,**kwargs):
                stepSize = self.sbStepSize.value()
                vUp   = checkv(self.biasVoltage + stepSize)
                vDown = checkv(self.biasVoltage - stepSize)
                self.lblStepUp.setText("to {v} volts".format(v=str(vUp)))
                self.lblStepDown.setText("to {v} volts".format(v=str(vDown)))

        def changeMeasurementInterval(self,*args,**kwargs):
                newInterval = self.sbMeasurementInterval.value()
                self.measurementInterval = newInterval
        def changePlotRefreshInterval(self,*args,**kwargs):
                newInterval = self.sbPlotRefreshInterval.value()
                self.plotRefreshInterval = newInterval



                
class mainDefault(gui.QMainWindow):
        def __init__(self):
                super(mainDefault,self).__init__(None)


if __name__ == '__main__':
        app = gui.QApplication(sys.argv)
        m = mainDesigner()
        m.show()
        app.exec_()
        m.timer.stop()
        data = numpy.array(m.data)
        data = data.swapaxes(0,1)
        CHECK_FOLDER=os.path.isdir(dpath)
        if not CHECK_FOLDER:
                os.makedirs(dpath)
        numpy.savetxt(os.sep.join(['data',f]),data)
        print("Saved data as {f}".format(f=f))
        m.s.close()   #safely disconnects from the Keithley before exiting
        sys.exit()







