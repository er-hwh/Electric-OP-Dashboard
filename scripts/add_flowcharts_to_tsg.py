import json

with open('static/data/loco_troubleshooting.json', 'r', encoding='utf-8') as f:
    topics = json.load(f)

flowcharts_data = {
    "TSG-3P-01": {
        "title": "3-Phase Pantograph Raising Decision Flowchart",
        "summary": "Step-by-step diagnostic sequence to identify pneumatic, electrical, and interlock reasons when Pantograph fails to raise or drops immediately.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Fault Detected: Panto Fails to Raise",
                "desc": "ZPT switch pressed to UP (pos 1), but Panto does not rise or drops immediately. No OHE tension indication.",
                "location": "Driver Cab Desk (Cab-1 / Cab-2)",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "decision",
                "title": "Check Auxiliary Reservoir (RS) Pressure",
                "desc": "Examine the RS pressure gauge in Machine Room No. 2. Is RS pressure equal to or greater than 5.2 kg/cm²?",
                "location": "Pneumatic Panel / Machine Room 2",
                "options": [
                    {"label": "YES (Pressure >= 5.2 kg/cm²)", "next_step": 4, "color": "success"},
                    {"label": "NO (Pressure Low < 5.2 kg/cm²)", "next_step": 3, "color": "danger"}
                ]
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Start Baby Compressor (MCPA)",
                "desc": "Switch ON Auxiliary Compressor (MCPA) toggle switch on panel SB-2. Run MCPA until RS pressure builds up to at least 6.0 kg/cm².",
                "location": "Auxiliary Cubicle SB-2",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "decision",
                "title": "Verify Emergency Stop & IG-38 Key Interlocks",
                "desc": "Are both Cab Emergency Stop buttons released and Key IG-38 in Cab-1 locked in vertical position?",
                "location": "Cabs & Pneumatic Panel",
                "options": [
                    {"label": "YES (Interlocks Normal)", "next_step": 5, "color": "success"},
                    {"label": "NO (Emergency Pressed / Key Loose)", "next_step": 6, "color": "warning"}
                ]
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Select Alternate Pantograph via Switch 125",
                "desc": "Rotate Panto Selector Switch 125 on Pneumatic Panel to position 1 (Panto-1) or position 2 (Panto-2) instead of Auto.",
                "location": "Pneumatic Panel",
                "next_step": 7
            },
            {
                "step_num": 6,
                "type": "action",
                "title": "Twist Release Emergency Stop & Reset MCB 127.12",
                "desc": "Twist and release Emergency Stop buttons in both cabs. Inspect and reset MCB 127.12 in Auxiliary Cubicle HB-2.",
                "location": "Cab Desks & HB-2 Panel",
                "next_step": 7
            },
            {
                "step_num": 7,
                "type": "success",
                "title": "Panto Raised Successfully",
                "desc": "Pantograph makes firm contact with OHE. U-meter registers 25 kV. Proceed with closing Main Circuit Breaker (VCB).",
                "location": "Locomotive Roof / OHE Contact",
                "next_step": None
            },
            {
                "step_num": 8,
                "type": "escalate",
                "title": "Escalation: Contact TLC",
                "desc": "If Panto still fails to raise, visually inspect carbon strip and roof equipment for physical damage. Contact TLC on 22328.",
                "location": "Traction Loco Control: 22328",
                "next_step": None
            }
        ]
    },
    "TSG-3P-02": {
        "title": "3-Phase VCB / DJ Closing & Holding Flowchart",
        "summary": "Procedural decision tree to diagnose VCB closing failures, OHE voltage boundary errors, and node interlock trips.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Fault Detected: VCB Fails to Close",
                "desc": "BLDJ pressed to close VCB, but VCB does not close or trips out immediately. LSDJ lamp remains continuously glowing.",
                "location": "Driver Desk / Cab Display",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "decision",
                "title": "Check OHE Voltage on U-Meter",
                "desc": "Check line voltmeter (U-Meter) on Cab Desk. Is OHE line voltage within permissible limits (17.5 kV to 30.0 kV)?",
                "location": "Driver Cab Desk Voltmeter",
                "options": [
                    {"label": "YES (OHE Voltage 17.5 - 30 kV)", "next_step": 3, "color": "success"},
                    {"label": "NO (No Tension / Voltage < 17.5 kV)", "next_step": 4, "color": "danger"}
                ]
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Verify Cab Handles & Press BLDJ",
                "desc": "Ensure Reverser handle (MP) is in '0' (Neutral) and TE/BE throttle is at '0'. Press and hold BLDJ for 2-3 seconds until LSDJ extinguishes.",
                "location": "Driver Cab Master Controller",
                "next_step": 5
            },
            {
                "step_num": 4,
                "type": "escalate",
                "title": "OHE Voltage Deficit -> Inform TLC",
                "desc": "OHE No Tension or out-of-range voltage. Contact Traction Loco Control (TLC: 22328 / PCNL: 22666). Await power restoration.",
                "location": "Traction Loco Control: 22328",
                "next_step": None
            },
            {
                "step_num": 5,
                "type": "decision",
                "title": "Did VCB Close and LSDJ Extinguish?",
                "desc": "Listen for heavy pneumatic latching sound of VCB and observe LSDJ indication on desk.",
                "location": "Driver Cab Console",
                "options": [
                    {"label": "YES (VCB Latched & LSDJ OFF)", "next_step": 6, "color": "success"},
                    {"label": "NO (VCB Tripped Again)", "next_step": 7, "color": "danger"}
                ]
            },
            {
                "step_num": 6,
                "type": "success",
                "title": "VCB Successfully Latched",
                "desc": "VCB is holding. Auxiliary converters BUR-1/2/3 start in sequence. Loco is ready to develop tractive effort.",
                "location": "Machine Room & Roof",
                "next_step": None
            },
            {
                "step_num": 7,
                "type": "action",
                "title": "Check MCBs 127.1 / 127.2 & Soft Reset CE",
                "desc": "Check and reset MCB 127.1 (HB-1) & MCB 127.2 (HB-2). Ensure MR pressure >= 6.4 kg/cm² on switch 269.6. Perform soft restart of CE (Key D OFF for 5 min).",
                "location": "HB-1 / HB-2 Cubicles",
                "next_step": 8
            },
            {
                "step_num": 8,
                "type": "escalate",
                "title": "VCB Actuator Failure -> Call TLC",
                "desc": "If VCB fails to close after CE restart, internal pneumatic valve or vacuum bottle fault suspected. Call TLC (22328).",
                "location": "Traction Loco Control: 22328",
                "next_step": None
            }
        ]
    },
    "TSG-3P-03": {
        "title": "3-Phase Auxiliary Converter (BUR 1/2/3) Tripping Flowchart",
        "summary": "Automatic reconfiguration check and soft restart sequence for auxiliary converter bus-tie contactors.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Auxiliary Converter Fault Displayed",
                "desc": "Diagnostic screen displays 'Auxiliary Converter Fault' (F0201P1 / F0202P1). Warning lamp LSFI blinks.",
                "location": "Driver Cab Display (DDS)",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Identify Failed BUR Subsystem on Screen",
                "desc": "Navigate to Subsystem 02 on DDS screen. Identify whether BUR-1, BUR-2, or BUR-3 has tripped.",
                "location": "DDS Screen Subsystem 02",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "decision",
                "title": "Did Auto Reconfiguration Succeed?",
                "desc": "Check if bus-tie contactors 52/1, 52/3 automatically closed to power blowers through remaining 2 BURs.",
                "location": "DDS Status Display",
                "options": [
                    {"label": "YES (2-BUR Mode Active)", "next_step": 4, "color": "success"},
                    {"label": "NO (All Auxiliaries Lost)", "next_step": 5, "color": "danger"}
                ]
            },
            {
                "step_num": 4,
                "type": "success",
                "title": "2-BUR Mode Operational",
                "desc": "Reconfiguration successful. All essential cooling blowers running. Continue train operation at permitted load. Log in Loco Book.",
                "location": "Machine Room Blowers",
                "next_step": None
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Stop Train Safely & Perform CE Restart",
                "desc": "Bring train to complete stop. Lower panto and open VCB. Turn Control Electronics Key 'D' to OFF. Wait 5 full minutes.",
                "location": "Driver Cab Desk Key 'D'",
                "next_step": 6
            },
            {
                "step_num": 6,
                "type": "action",
                "title": "Re-energise CE & Re-raise Panto",
                "desc": "Turn Key 'D' to ON, raise panto and close VCB. Verify whether BURs reboot and latch normally.",
                "location": "Driver Cab Desk",
                "next_step": 7
            },
            {
                "step_num": 7,
                "type": "escalate",
                "title": "Persistent BUR Lockout -> Call TLC",
                "desc": "If BUR trips again and blowers do not run, do NOT notch up traction to prevent motor overheating. Inform TLC on 22328.",
                "location": "Traction Loco Control: 22328",
                "next_step": None
            }
        ]
    },
    "TSG-3P-04": {
        "title": "3-Phase Traction Converter Isolation (Switch 154) Flowchart",
        "summary": "Procedural guide to isolate a defective traction bogie and operate on 50% tractive effort.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Traction Converter Failure Displayed",
                "desc": "DDS alerts 'Traction Converter-1 Fault' (F0301P1) or 'Traction Converter-2 Fault' (F0401P1). Loss of tractive effort in one bogie.",
                "location": "Driver Cab Display (DDS)",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Bring Train to Halt on Level Track",
                "desc": "Safely stop train. Lower panto and open VCB. Turn Control Electronics Key 'D' to OFF position.",
                "location": "Driver Cab Desk",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Locate Bogie Isolation Switch 154",
                "desc": "Enter Machine Room No. 1 and locate rotary Switch 154 on Auxiliary Cubicle SB-1.",
                "location": "Auxiliary Cubicle SB-1",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "decision",
                "title": "Select Faulty Bogie to Isolate",
                "desc": "Rotate Switch 154 to isolate the failed converter identified on DDS:",
                "location": "Switch 154 (SB-1)",
                "options": [
                    {"label": "Position 'I' (Isolate Bogie 1 / SR-1)", "next_step": 5, "color": "warning"},
                    {"label": "Position 'II' (Isolate Bogie 2 / SR-2)", "next_step": 5, "color": "warning"}
                ]
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Reboot CE & Energise Healthy Bogie",
                "desc": "Turn Key 'D' to ON, raise panto, close VCB. DDS will acknowledge isolation and show healthy bogie in green.",
                "location": "Driver Cab Console",
                "next_step": 6
            },
            {
                "step_num": 6,
                "type": "success",
                "title": "Single-Bogie 50% TE Traction Restored",
                "desc": "Locomotive can operate on 50% tractive effort. Clear block section safely to nearest junction. Inform TLC on 22328.",
                "location": "Track Section",
                "next_step": None
            }
        ]
    },
    "TSG-3P-05": {
        "title": "Vigilance Control Device (VCD) Penalty Reset Flowchart",
        "summary": "Mandatory safety sequence to clear VCD penalty brake application and recharge brake pipe.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "VCD Penalty Brake Applied",
                "desc": "Flashing VCD indicator and buzzer unacknowledged for 76 seconds. BP exhausts automatically to 2.8 - 3.0 kg/cm².",
                "location": "Driver Cab Console",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Throttle & Reverser to '0' Neutral",
                "desc": "Immediately bring TE/BE throttle handle to '0'. Move Reverser handle (MP) to '0' (Neutral).",
                "location": "Driver Cab Master Controller",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Ensure Complete Train Halt",
                "desc": "Wait for train to come to a standstill. NEVER attempt to reset VCD penalty while train is rolling!",
                "location": "Trackside / Train Rake",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Wait 160 Seconds Penalty Lock Period",
                "desc": "Observe cab clock / watch. Wait exactly 160 seconds for internal electronic penalty timer to expire.",
                "location": "Cab Clock Timer",
                "next_step": 5
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Press VCD Reset Switch (237.1)",
                "desc": "Press VCD Reset Push Button Switch 237.1 on Assistant Loco Pilot's desk for 2-3 seconds.",
                "location": "Assistant Loco Pilot Desk",
                "next_step": 6
            },
            {
                "step_num": 6,
                "type": "decision",
                "title": "Does Brake Pipe (BP) Recharge to 5.0 kg/cm²?",
                "desc": "Watch duplex air pressure gauge on cab desk. Does BP pressure build up smoothly to 5.0 kg/cm²?",
                "location": "Cab Air Brake Gauge",
                "options": [
                    {"label": "YES (BP at 5.0 kg/cm²)", "next_step": 7, "color": "success"},
                    {"label": "NO (BP Not Building Up)", "next_step": 8, "color": "danger"}
                ]
            },
            {
                "step_num": 7,
                "type": "success",
                "title": "Penalty Cleared & Normal Operation Resumed",
                "desc": "Brakes released across the train. Resume normal journey. Enter penalty details in VCD Log Book.",
                "location": "Running Train",
                "next_step": None
            },
            {
                "step_num": 8,
                "type": "action",
                "title": "Isolate Cock 74 & Trip MCB 127.9/1",
                "desc": "Isolate VCD Pneumatic Cock (Cock 74) on Pneumatic Panel. Switch OFF MCB 127.9/1 in SB-1. Advise TLC (22328).",
                "location": "Pneumatic Panel & SB-1",
                "next_step": None
            }
        ]
    },
    "TSG-3P-06": {
        "title": "Brake Pipe (BP) Deficit & Exhaust Troubleshooting Flowchart",
        "summary": "Pneumatic diagnostic flow to identify train pipe ruptures, cock positions, and emergency valve leaks.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Brake Pipe Pressure Deficit Detected",
                "desc": "BP pressure drops below 5.0 kg/cm² or continuous heavy hiss of air exhaust heard from cab or train rake.",
                "location": "Cab Duplex Pressure Gauge",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "decision",
                "title": "Verify A-9 Handle & Lead/Trail Switch",
                "desc": "Is A-9 automatic brake handle in 'RUN' position and Lead/Trail switch set properly to 'Lead'?",
                "location": "Driver Cab Brake Controller",
                "options": [
                    {"label": "YES (A-9 in RUN & Lead Active)", "next_step": 3, "color": "success"},
                    {"label": "NO (A-9 displaced / Wrong Mode)", "next_step": 4, "color": "warning"}
                ]
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Check Emergency Valve Cock (Cock 70)",
                "desc": "Inspect Assistant Loco Pilot's Emergency Brake Cock (Cock 70) in both cabs. Ensure handle is tightly closed.",
                "location": "Cab-1 & Cab-2 Desks",
                "next_step": 5
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Correct A-9 Handle Position",
                "desc": "Set A-9 handle firmly in RUN position. In trailing/banking cabs, ensure A-9 is pinned in Neutral.",
                "location": "Cab Brake Controller",
                "next_step": 5
            },
            {
                "step_num": 5,
                "type": "decision",
                "title": "Check MR Main Reservoir Pressure",
                "desc": "Is Main Reservoir (MR) pressure between 8.5 and 10.0 kg/cm²? Are main compressors charging normally?",
                "location": "Cab MR Gauge",
                "options": [
                    {"label": "YES (MR Pressure >= 8.5 kg/cm²)", "next_step": 6, "color": "success"},
                    {"label": "NO (MR Low < 8.5 kg/cm²)", "next_step": 7, "color": "danger"}
                ]
            },
            {
                "step_num": 6,
                "type": "decision",
                "title": "Train Rake vs Locomotive Leakage Check",
                "desc": "Close BP angle cock at rear of locomotive. Does loco BP charge to 5.0 kg/cm²?",
                "location": "Rear Buffer Beam Angle Cock",
                "options": [
                    {"label": "YES (Loco OK -> Leakage is in Train Rake)", "next_step": 8, "color": "warning"},
                    {"label": "NO (Leakage is Inside Locomotive)", "next_step": 9, "color": "danger"}
                ]
            },
            {
                "step_num": 7,
                "type": "action",
                "title": "Check Compressors & Drain Cocks",
                "desc": "Check BLCP switch is in 'AUTO' or 'MAN'. Inspect auto-drain valves and moisture separator for continuous blowing.",
                "location": "Machine Room Compressors",
                "next_step": 5
            },
            {
                "step_num": 8,
                "type": "action",
                "title": "Examine Train Rake with Guard",
                "desc": "Coordinate with Guard: walk the rake to identify uncoupled hose, open passenger alarm chain (ACP), or open guard van valve.",
                "location": "Passenger / Freight Rake",
                "next_step": 10
            },
            {
                "step_num": 9,
                "type": "action",
                "title": "Check Distributor Valve & IP Valve",
                "desc": "Inspect C3W distributor valve isolating cock on pneumatic panel. If blowing continuously, tap gently or isolate.",
                "location": "Pneumatic Panel",
                "next_step": 10
            },
            {
                "step_num": 10,
                "type": "success",
                "title": "Brake Pipe Pressure Restored to 5.0 kg/cm²",
                "desc": "Leak sealed. BP holds steady at 5.0 kg/cm², FP at 6.0 kg/cm². Perform brake feel test and proceed.",
                "location": "Loco Cab & Train",
                "next_step": None
            }
        ]
    },
    "TSG-3P-07": {
        "title": "Hotel Load Converter (HOG) Troubleshooting Flowchart",
        "summary": "Checklist sequence to restore power to train coaching air conditioning and lighting.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "HOG Tripped / Passenger Rake Power Off",
                "desc": "Hotel Load Converter trips. AC and lights in coaching stock shut down. DDS shows HOG Inverter Fault.",
                "location": "DDS Screen & Coaching Rake",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Inspect UIC IV Coupler Cable",
                "desc": "Visually examine Hotel Load IV couplers between loco and front power car for loose pins or water ingress.",
                "location": "Buffer Beam Couplers",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Open VCB & Reset HOG MCB",
                "desc": "Open VCB. Enter Machine Room and locate HOG Control Cubicle. Reset tripped HOG control circuit breakers.",
                "location": "HOG Cubicle Machine Room",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Re-close VCB & Press HOG ON",
                "desc": "Re-close VCB. Press HOG ON push button on Driver Desk. Observe HOG voltage build-up on display.",
                "location": "Driver Cab Desk",
                "next_step": 5
            },
            {
                "step_num": 5,
                "type": "decision",
                "title": "Does HOG Supply 750V 3-Phase to Rake?",
                "desc": "Check HOG panel voltmeter. Is 750V AC active and coaching supply restored?",
                "location": "HOG Display Panel",
                "options": [
                    {"label": "YES (750V Active & Coaches Powered)", "next_step": 6, "color": "success"},
                    {"label": "NO (HOG Trips Again)", "next_step": 7, "color": "danger"}
                ]
            },
            {
                "step_num": 6,
                "type": "success",
                "title": "HOG Normal Operation Restored",
                "desc": "Passenger coaches powered via locomotive. Advise Train Superintendent. Proceed on run.",
                "location": "Coaching Train",
                "next_step": None
            },
            {
                "step_num": 7,
                "type": "escalate",
                "title": "Start DG Power Car (EOG Mode) -> Call TLC",
                "desc": "Internal HOG inverter failure. Advise Guard & AC staff to start DG set in Power Car. Inform TLC (22328).",
                "location": "TLC (22328) & Power Car",
                "next_step": None
            }
        ]
    },
    "TSG-CV-01": {
        "title": "Conventional WAP-4 / WAG-7 DJ Closing Decision Flowchart",
        "summary": "Step-by-step relay sequence (Q44, Q118, Q45) and pneumatic checks when BLDJ is pressed but LSDJ remains glowing.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "DJ Not Closing (LSDJ Glowing Continuously)",
                "desc": "BLDJ push button pressed, but LSDJ remains lit. DJ does not close with audible latching sound.",
                "location": "Cab Desk Indicator Panel",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "decision",
                "title": "Check Battery Voltage (>= 90V)",
                "desc": "Check Control Battery Voltmeter. Is battery voltage equal to or higher than 90 Volts?",
                "location": "Cab Voltmeter",
                "options": [
                    {"label": "YES (Voltage >= 90V)", "next_step": 3, "color": "success"},
                    {"label": "NO (Voltage Low < 90V)", "next_step": 4, "color": "danger"}
                ]
            },
            {
                "step_num": 3,
                "type": "decision",
                "title": "Check Auxiliary Reservoir (RS) Pressure",
                "desc": "Check RS pressure gauge on Pneumatic Panel. Is RS pressure >= 6.5 kg/cm²?",
                "location": "Pneumatic Panel Gauge",
                "options": [
                    {"label": "YES (RS Pressure >= 6.5 kg/cm²)", "next_step": 5, "color": "success"},
                    {"label": "NO (RS Pressure Low < 6.5 kg/cm²)", "next_step": 6, "color": "danger"}
                ]
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Check Battery Knife Switch & CHBA",
                "desc": "Check Battery Knife Switch (HOBA). Check Battery Charger (CHBA) MCB. Ensure proper terminal connection.",
                "location": "Battery Box & Switch Panel",
                "next_step": 2
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Verify Relay Q44 & Q118 Positions",
                "desc": "Inspect Relay Panel: Ensure Tap Changer GR is on '0' notch. Ensure Relay Q44 and Q118 are in de-energized normal state.",
                "location": "Relay Panel-1",
                "next_step": 7
            },
            {
                "step_num": 6,
                "type": "action",
                "title": "Start Baby Compressor (MCPA)",
                "desc": "Start Baby Compressor (MCPA) using ZCPA switch. Build RS pressure up to at least 7.5 kg/cm².",
                "location": "Pneumatic Panel",
                "next_step": 3
            },
            {
                "step_num": 7,
                "type": "action",
                "title": "Operate BLDJ Push Button",
                "desc": "Press BLDJ firmly for 2 to 3 seconds until LSDJ extinguishes and UA line voltmeter kicks to 25 kV.",
                "location": "Driver Cab Desk",
                "next_step": 8
            },
            {
                "step_num": 8,
                "type": "success",
                "title": "DJ Closed Successfully",
                "desc": "LSDJ extinguished. UA meter shows 25 kV. Auxiliary motors pick up. Locomotive ready for notching.",
                "location": "Locomotive Roof & Cab",
                "next_step": None
            },
            {
                "step_num": 9,
                "type": "escalate",
                "title": "DJ Coil / Magnet Valve Fault -> Call TLC",
                "desc": "If DJ still does not close after verifying RS pressure and relays, call TLC on 22328 / PCNL on 22666.",
                "location": "Traction Loco Control: 22328",
                "next_step": None
            }
        ]
    },
    "TSG-CV-02": {
        "title": "Conventional DJ Tripping on 1st Notch / Run Flowchart",
        "summary": "Diagnostic sequence to identify dropped relay targets (QLM, QOP, Q20, Q44) and tap changer faults.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "DJ Trips on 1st Notch or on Run",
                "desc": "Moving MP throttle to notch 1 causes DJ to trip instantly, or DJ opens while running at speed.",
                "location": "Driver Cab Desk",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Inspect Relay Target Indicators",
                "desc": "Enter Machine Room and inspect target indicators on Relay Panels 1 & 2.",
                "location": "Relay Panel 1 & 2",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "decision",
                "title": "Which Target has Dropped?",
                "desc": "Identify the dropped safety relay target flag:",
                "location": "Relay Panel",
                "options": [
                    {"label": "QLM (Primary Overcurrent)", "next_step": 4, "color": "danger"},
                    {"label": "QOP (Traction Circuit Earth Fault)", "next_step": 5, "color": "danger"},
                    {"label": "Q20 (Line Overvoltage)", "next_step": 6, "color": "warning"},
                    {"label": "No Target Dropped (Q44/Q118/Pressure)", "next_step": 7, "color": "info"}
                ]
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Inspect Transformer Oil & Primary Bushing",
                "desc": "QLM drop indicates transformer primary surge. Check transformer oil gauge and explosion vent. Reset QLM target once only.",
                "location": "Main Transformer Tank",
                "next_step": 8
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Isolate Traction Motors via HVMT",
                "desc": "Earth fault detected. Rotate HVMT switch to isolate TM-1/2 or TM-3/4 or TM-5/6 one by one to pinpoint grounded motor.",
                "location": "HVMT Switch Panel",
                "next_step": 8
            },
            {
                "step_num": 6,
                "type": "action",
                "title": "Wait for OHE Voltage Stabilization",
                "desc": "Q20 drops when OHE exceeds 30 kV. Wait for tension stabilization before re-closing DJ.",
                "location": "Driver Cab Voltmeter",
                "next_step": 8
            },
            {
                "step_num": 7,
                "type": "action",
                "title": "Check Control Air & Tap Changer GR",
                "desc": "Ensure Control Air Pressure >= 5.0 kg/cm². Ensure tap changer GR returns freely to '0' without sticking.",
                "location": "Tap Changer GR Cubicle",
                "next_step": 8
            },
            {
                "step_num": 8,
                "type": "success",
                "title": "Target Reset & Traction Resumed",
                "desc": "Re-close DJ. Notch up smoothly with sanding to avoid wheel slip. If trips again, contact TLC (22328).",
                "location": "Driver Cab",
                "next_step": None
            }
        ]
    },
    "TSG-CV-03": {
        "title": "Conventional Auxiliary Motors & SIV Tripping Flowchart",
        "summary": "Relay QSIT verification, SIV inverter reset, and auxiliary motor protection sequence.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "SIV Tripped / Auxiliary Motors Failed to Start",
                "desc": "LSAF warning lamp glows or traction motor/oil cooling blowers (MVRH, MVMT) do not start after DJ close.",
                "location": "Cab Desk & SIV Panel",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Inspect SIV Display Unit in Machine Room",
                "desc": "Read diagnostic LED display on Static Inverter (SIV) cubicle. Note fault code (Earth Fault, DC Overvoltage, or Overload).",
                "location": "SIV Cubicle Machine Room",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Press SIV Reset Push Button",
                "desc": "Press SIV Reset button on SIV front panel for 3 seconds to clear transient inverter trip.",
                "location": "SIV Panel",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "decision",
                "title": "Check Relay QSIT Position",
                "desc": "Examine Relay QSIT on relay panel. Is QSIT target dropped or in normal picked-up state?",
                "location": "Relay Panel",
                "options": [
                    {"label": "QSIT Picked Up (Normal)", "next_step": 5, "color": "success"},
                    {"label": "QSIT Dropped (Internal Trip)", "next_step": 6, "color": "danger"}
                ]
            },
            {
                "step_num": 5,
                "type": "success",
                "title": "Auxiliary Motors Running Smoothly",
                "desc": "All auxiliary motors start up within 15 seconds. LSAF lamp extinguishes. Resume train working.",
                "location": "Machine Room Blowers",
                "next_step": None
            },
            {
                "step_num": 6,
                "type": "escalate",
                "title": "Persistent SIV Fault -> Consult TLC",
                "desc": "If QSIT drops repeatedly, an auxiliary motor winding may be shorted. Consult TLC (22328) for SIV bypass procedure.",
                "location": "TLC: 22328 / PCNL: 22666",
                "next_step": None
            }
        ]
    },
    "TSG-SOP-01": {
        "title": "Neutral Section Coasting Procedure (GR 17.07) Flowchart",
        "summary": "Spatial procedural sequence from 500m warning board to clearing dead section and resuming traction.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Sighting 500 Metres Warning Board",
                "desc": "Loco Pilot sights the 500m Neutral Section Warning Board beside the track ahead.",
                "location": "Trackside 500m Ahead",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "At 500m Board: Drop Throttle to '0'",
                "desc": "Cut off tractive effort immediately. Return throttle / TE/BE handle to '0' position.",
                "location": "Driver Cab Master Controller",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "At 250m Board: Open DJ / VCB",
                "desc": "Sighting 250m Warning Board: Press BLDJ to open DJ / VCB. Confirm LSDJ glows.",
                "location": "Driver Cab Desk",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "decision",
                "title": "Confirm Zero OHE Voltage on U-Meter",
                "desc": "Verify line voltmeter reads 0 kV while panto remains raised. Train coasts through dead section on momentum.",
                "location": "Cab Voltmeter",
                "options": [
                    {"label": "Voltage 0 kV (Safely De-energised)", "next_step": 5, "color": "success"},
                    {"label": "DJ Failed to Open (Arcing Danger!)", "next_step": 6, "color": "danger"}
                ]
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Coast Past Neutral Section Cleared Board",
                "desc": "Wait until locomotive pantograph completely crosses the 'Neutral Section Cleared / Resume' board.",
                "location": "OHE Overhead Line",
                "next_step": 7
            },
            {
                "step_num": 6,
                "type": "action",
                "title": "Emergency Lower Panto via ZPT",
                "desc": "If DJ fails to open, immediately lower pantograph via ZPT switch to avoid shattering OHE insulators!",
                "location": "ZPT Switch Cab Desk",
                "next_step": 5
            },
            {
                "step_num": 7,
                "type": "action",
                "title": "Re-close DJ / VCB",
                "desc": "Press BLDJ to re-close DJ/VCB. Confirm LSDJ extinguishes and line voltmeter indicates 25 kV.",
                "location": "Driver Cab Desk",
                "next_step": 8
            },
            {
                "step_num": 8,
                "type": "success",
                "title": "Resume Normal Notching",
                "desc": "Notch up traction gradually. Maintain permissible sectional speed without wheel slipping.",
                "location": "Running Train",
                "next_step": None
            }
        ]
    },
    "TSG-SOP-02": {
        "title": "Passing Automatic Stop Signal at 'ON' (GR 9.02) Flowchart",
        "summary": "Mandatory safety timings, whistle codes, and restricted speed limits when passing an Automatic Stop Signal at Danger.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Automatic Stop Signal Displaying 'Danger'",
                "desc": "Loco Pilot sights an Automatic Stop Signal showing Red / 'ON' aspect.",
                "location": "Trackside Automatic Signal",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "action",
                "title": "Stop Train in Rear of the Signal",
                "desc": "Bring train to a complete halt before the foot of the signal. Apply loco and train brakes.",
                "location": "In Rear of Signal",
                "next_step": 3
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Mandatory Halt: 1 Min Day / 2 Min Night",
                "desc": "Wait exactly 1 minute by day or 2 minutes by night with train stationary.",
                "location": "Cab Clock Timer",
                "next_step": 4
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Whistle Code & Signal Exchange with Guard",
                "desc": "Sound one long continuous whistle. Exchange hand signals (Red/Green flag or lamp) with the Guard.",
                "location": "Locomotive Horn & Guard Van",
                "next_step": 5
            },
            {
                "step_num": 5,
                "type": "decision",
                "title": "Assess Track Visibility Conditions",
                "desc": "Is visibility clear, or is it impaired by fog, heavy rain, dust storm, or sharp curves?",
                "location": "Track Forward View",
                "options": [
                    {"label": "Clear Visibility (Normal)", "next_step": 6, "color": "success"},
                    {"label": "Impaired Visibility / Curvature", "next_step": 7, "color": "warning"}
                ]
            },
            {
                "step_num": 6,
                "type": "action",
                "title": "Proceed at Speed Not Exceeding 15 kmph",
                "desc": "Start train cautiously. Maximum speed must not exceed 15 kmph. Be ready to stop short of any obstruction.",
                "location": "Automatic Block Section",
                "next_step": 8
            },
            {
                "step_num": 7,
                "type": "action",
                "title": "Restrict Speed to 10 kmph or Walking Pace",
                "desc": "Under impaired visibility or curve, restrict speed to 10 kmph or walking pace so train can stop within visible distance.",
                "location": "Automatic Block Section",
                "next_step": 8
            },
            {
                "step_num": 8,
                "type": "success",
                "title": "Arrive at Next Stop Signal",
                "desc": "Maintain cautious speed until next Stop Signal ahead is sighted. Obey its aspect strictly.",
                "location": "Next Stop Signal",
                "next_step": None
            }
        ]
    },
    "TSG-SOP-03": {
        "title": "Foggy Weather & Detonator Protection (GR 3.61) Flowchart",
        "summary": "Visibility assessment, detonator placement distances, and speed restrictions during thick fog.",
        "steps": [
            {
                "step_num": 1,
                "type": "start",
                "title": "Foggy Weather Impairing Visibility",
                "desc": "Thick fog, tempestuous weather, or dust storm reduces visibility on the section.",
                "location": "Station & Block Section",
                "next_step": 2
            },
            {
                "step_num": 2,
                "type": "decision",
                "title": "Station Master Visibility Test Post Check",
                "desc": "Station Master checks Visibility Test Object / Post (180m from SM office). Can it be seen?",
                "location": "Station Master Office (180m)",
                "options": [
                    {"label": "YES (Visibility Object Visible)", "next_step": 3, "color": "success"},
                    {"label": "NO (Cannot See Object -> Thick Fog)", "next_step": 4, "color": "danger"}
                ]
            },
            {
                "step_num": 3,
                "type": "action",
                "title": "Normal Train Working Maintained",
                "desc": "Visibility is adequate. Detonator protection not required. Maintain standard sectional speeds.",
                "location": "Station Section",
                "next_step": None
            },
            {
                "step_num": 4,
                "type": "action",
                "title": "Depute 2 Fog Signalmen with 24 Detonators",
                "desc": "Station Master immediately calls 2 trained fog signalmen. Issue 24 detonators each with hand signal lamps.",
                "location": "Station Detonator Register",
                "next_step": 5
            },
            {
                "step_num": 5,
                "type": "action",
                "title": "Place 2 Detonators 10m Apart at 270m",
                "desc": "Fog signalman places two detonators on rail 10 metres apart, at a distance of 270 metres in rear of First Stop Signal.",
                "location": "270m in Rear of Outer/Distant",
                "next_step": 6
            },
            {
                "step_num": 6,
                "type": "decision",
                "title": "Is Locomotive Equipped with Fog Safe Device (FSD)?",
                "desc": "Check whether active GPS-based Fog Safe Device is provided in driver cab:",
                "location": "Driver Cab FSD Unit",
                "options": [
                    {"label": "YES (FSD Available & Functional)", "next_step": 7, "color": "success"},
                    {"label": "NO (FSD Not Available)", "next_step": 8, "color": "warning"}
                ]
            },
            {
                "step_num": 7,
                "type": "success",
                "title": "Proceed with FSD: Max 75 kmph",
                "desc": "Loco Pilot guided by FSD audio-visual countdown. Maximum speed permissible is 75 kmph.",
                "location": "Running Train",
                "next_step": None
            },
            {
                "step_num": 8,
                "type": "success",
                "title": "Proceed Without FSD: Max 60 kmph",
                "desc": "Speed restricted to maximum 60 kmph. Extreme alertness: sound intermittent whistles and observe detonators.",
                "location": "Running Train",
                "next_step": None
            }
        ]
    }
}

count_updated = 0
for t in topics:
    topic_id = t["id"]
    if topic_id in flowcharts_data:
        t["flowchart"] = flowcharts_data[topic_id]
        count_updated += 1
    else:
        # Not relevant for flowchart
        t["flowchart"] = None

print(f"Updated {count_updated} relevant topics with rich animated flowcharts.")

with open('static/data/loco_troubleshooting.json', 'w', encoding='utf-8') as f:
    json.dump(topics, f, indent=2, ensure_ascii=False)

print("Saved updated static/data/loco_troubleshooting.json successfully!")
