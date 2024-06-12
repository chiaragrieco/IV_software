Amina Li, UCSB 2022

== TestStandUI.py ==
-connects to and controls Keithley [requires cable from Keithley RS-232 port to computer USB]
-Keithley should be on (output shouldn't be on) before running script
-closing UI window writes data to file and safely turns off Keithley
TO RUN:
~ right click TestStandUI.py -> Edit with IDLE  OR
    start IDLE [desktop shortcut] -> File [menu along top of window] -> Open -> TestStandUI.py
~ adjust default run settings if desired
~ Run [menu along top of window] -> Run Module  OR  F5
~ adjust additional settings in UI window if desired
~ "Step Voltage", "Step Up", and "Step Down" are clickable buttons if needed
~ after settings are satisfactory, top right checkbox used to start voltage stepping
	^the plots will begin updating as soon as the window is open (this does not mean it is running steps)

== Keithley2410.py ==
-used by TestStandUI, contains specific syntax to communicate with Keithley

== mainWindow.py == *inside interface folder*
-used by TestStandUI, sets up the UI window