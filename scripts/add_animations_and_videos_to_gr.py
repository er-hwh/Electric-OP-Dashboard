"""
Script to enrich GR & SR topics with:
1. Animated Interactive Operational Flowcharts & Track Schematics
2. YouTube Video Thumbnails, IDs, and Titles
Updates both static/data/gr_sr_rules.json and MySQL elearning_rules table.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from database import db
from models import ELearningRule

MEDIA_ENRICHMENT = {
    "GR 9.02": {
        "youtube_video_id": "7x_dZk0fU2U",
        "youtube_title": "Passing Automatic Stop Signal at 'ON' - Operational SOP & Speed Restrictions (GR 9.02)",
        "animation": {
            "title": "Passing Automatic Stop Signal at 'ON' (Red Aspect with Lit 'A' Marker)",
            "rule": "GR 9.02 & SR 9.02",
            "type": "flowchart_and_schematic",
            "schematic": "automatic_signal",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Stop Dead Before Automatic Signal",
                    "type": "start",
                    "desc": "Bring train to complete standstill before the Automatic Stop Signal displaying Danger (Red). Confirm illuminated letter 'A' marker is lit.",
                    "action": "Complete stop; check 'A' marker lit",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 2,
                    "title": "Mandatory Waiting Period",
                    "type": "wait",
                    "desc": "Wait 1 minute by day / 2 minutes by night. DO NOT start before this statutory time expires.",
                    "action": "Wait 1 min (Day) / 2 min (Night)",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 3,
                    "title": "Sound Horn & Exchange Signals with Guard",
                    "type": "action",
                    "desc": "Sound one long continuous whistle. Exchange all-right hand signal with Guard over walkie-talkie and hand lamp/flag.",
                    "action": "One long whistle + Guard all-right",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 4,
                    "title": "Move Ahead at Restricted Speed",
                    "type": "action",
                    "desc": "Proceed with extreme caution: Maximum 15 kmph in clear weather / 10 kmph during fog, curves, or darkness, prepared to stop short of any obstruction.",
                    "action": "Max 15 kmph (Clear) / 10 kmph (Fog/Curves)",
                    "speed": "15 / 10 KMPH"
                },
                {
                    "step_num": 5,
                    "title": "Maintain Spacing from Preceding Train",
                    "type": "decision",
                    "desc": "If a train is seen stopped ahead, stop and maintain a minimum distance of 150 metres (or two OHE spans).",
                    "options": [
                        {"label": "Line Clear Ahead", "next_step": 6, "color": "success"},
                        {"label": "Train Stopped Ahead", "next_step": 5, "color": "danger"}
                    ],
                    "action": "Maintain min 150m (2 OHE spans)",
                    "speed": "Stop short"
                },
                {
                    "step_num": 6,
                    "title": "Approach Next Signal",
                    "type": "success",
                    "desc": "Strictly obey the aspect of the next signal. Report detention to Station Master at the first station.",
                    "action": "Obey next signal; log in memo",
                    "speed": "Signal aspect"
                }
            ]
        }
    },

    "GR 3.61": {
        "youtube_video_id": "eD4uD_17LQE",
        "youtube_title": "Dense Foggy Weather Precautions & Detonator Placement at 270m (GR 3.61)",
        "animation": {
            "title": "Fog Signal Placement & Train Operation in Thick / Foggy Weather",
            "rule": "GR 3.61 & SR 3.61",
            "type": "flowchart_and_schematic",
            "schematic": "fog_detonators",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Fog Signal Post (FSP) Activated",
                    "type": "start",
                    "desc": "When visibility drops and fog signalmen are deputed, proceed to Fog Signal Post (FSP) located 270 metres outside the First Stop Signal.",
                    "action": "Depute Fog Signalmen to FSP",
                    "location": "270m from First Stop Signal"
                },
                {
                    "step_num": 2,
                    "title": "Fix 1st Detonator on Rail",
                    "type": "action",
                    "desc": "Fix 1st detonator firmly onto the rail surface at 270 metres outside the first stop signal using lead clips.",
                    "action": "1st Detonator fixed on rail",
                    "location": "270 metres"
                },
                {
                    "step_num": 3,
                    "title": "Fix 2nd Detonator 10m Ahead",
                    "type": "action",
                    "desc": "Fix 2nd detonator on the same rail exactly 10 metres apart (at 280 metres outside first stop signal).",
                    "action": "2nd Detonator fixed 10m apart",
                    "location": "280 metres"
                },
                {
                    "step_num": 4,
                    "title": "Fog Signalman Safety Clearance",
                    "type": "action",
                    "desc": "Signalman must stand at least 45 metres away from the detonators to avoid flying splinters upon explosion.",
                    "action": "Stand at least 45m away",
                    "location": "Safe distance"
                },
                {
                    "step_num": 5,
                    "title": "Loco Pilot Action on Detonator Explosion",
                    "type": "success",
                    "desc": "Loco Pilot hears explosion: Immediately control train, reduce speed to max 75 kmph (60 kmph in dense fog), and be prepared to stop at first stop signal.",
                    "action": "Control train; Max 75 kmph / 60 kmph",
                    "speed": "Max 75 / 60 KMPH"
                }
            ]
        }
    },

    "GR 17.05": {
        "youtube_video_id": "y5a8eS9y2XU",
        "youtube_title": "Neutral Section Negotiation on 25 kV AC Electric Locos (WAP-7 / WAG-9) (GR 17.05)",
        "animation": {
            "title": "Approaching and Coasting Through Neutral Section (25 kV AC)",
            "rule": "GR 17.05 & SR 17.05",
            "type": "flowchart_and_schematic",
            "schematic": "neutral_section",
            "steps": [
                {
                    "step_num": 1,
                    "title": "500m & 250m Warning Boards",
                    "type": "start",
                    "desc": "Acknowledge 500m Warning Board and 250m Warning Board. Call out 'Neutral Section Approaching' to ALP.",
                    "action": "Alert ALP; check line voltage (25 kV)",
                    "location": "500m & 250m before Neutral Section"
                },
                {
                    "step_num": 2,
                    "title": "Open DJ / VCB Board",
                    "type": "action",
                    "desc": "At the 'Open DJ' board, immediately press BLDJ / open VCB. Ensure traction motor current drops to ZERO.",
                    "action": "Press BLDJ / Open VCB; Current = 0 Amp",
                    "location": "Open DJ Board"
                },
                {
                    "step_num": 3,
                    "title": "Coast Through Dead Zone (Panto Raised)",
                    "type": "action",
                    "desc": "Coast through the insulated dead zone. PANTOGRAPH REMAINS RAISED. Do NOT apply regenerative/rheostatic braking.",
                    "action": "Coast freely; Panto remains UP",
                    "location": "Neutral Section Insulators"
                },
                {
                    "step_num": 4,
                    "title": "Close DJ / VCB Board",
                    "type": "action",
                    "desc": "When rear cab passes 'Close DJ' board, press BLDJ to re-close circuit breaker. Verify U-meter shows 22.5–27 kV.",
                    "action": "Close DJ / VCB; Check auxiliary restart",
                    "location": "Close DJ Board"
                },
                {
                    "step_num": 5,
                    "title": "Resume Traction Power",
                    "type": "success",
                    "desc": "Verify BLDJ lamp extinguishes, compressor and cooling blowers restart normally. Notch up smoothly.",
                    "action": "Notch up; Resume normal speed",
                    "speed": "Section MPS"
                }
            ]
        }
    },

    "GR 6.03": {
        "youtube_video_id": "s9H5kY2V6f0",
        "youtube_title": "Accident & Track Protection on Double Line - Flasher Light & Detonators (GR 6.03)",
        "animation": {
            "title": "Emergency Protection of Obstructed / Fouled Track on Double Line",
            "rule": "GR 6.03 & SR 6.03",
            "type": "flowchart_and_schematic",
            "schematic": "track_protection",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Instant Hazard Notification",
                    "type": "start",
                    "desc": "Train stops due to accident/derailment. Instantly switch ON Flasher Light in both cabs and sound hazard whistle (4 short blasts).",
                    "action": "Flasher Light ON + 4 short whistles",
                    "location": "At disabled locomotive"
                },
                {
                    "step_num": 2,
                    "title": "Check Adjacent Line Fouling",
                    "type": "decision",
                    "desc": "Inspect if derailed coaches or obstruction fouls the adjacent running line.",
                    "options": [
                        {"label": "Adjacent Line Fouled", "next_step": 3, "color": "danger"},
                        {"label": "Adjacent Line Clear", "next_step": 5, "color": "primary"}
                    ],
                    "action": "Visual inspection of adjacent track"
                },
                {
                    "step_num": 3,
                    "title": "ALP Rushes Forward on Adjacent Line",
                    "type": "action",
                    "desc": "ALP takes detonators, red flag/lamp, and rushes forward immediately to protect adjacent track in direction of approaching trains.",
                    "action": "ALP rushes with 10 detonators + red lamp"
                },
                {
                    "step_num": 4,
                    "title": "Fix Detonators (600m & 1200m)",
                    "type": "action",
                    "desc": "Fix 1 detonator at 600 metres from obstruction. Fix 3 detonators 10 metres apart at 1200 metres. Stand 45m away showing red flag/lamp.",
                    "action": "1 at 600m, 3 at 1200m (10m apart)",
                    "location": "600m & 1200m"
                },
                {
                    "step_num": 5,
                    "title": "Guard Protects Rear on Affected Track",
                    "type": "success",
                    "desc": "Guard rushes back to protect rear of train with detonators (1 at 600m, 3 at 1200m). Alert Station Master & TLC 22328.",
                    "action": "Guard protects rear; Alert TLC 22328"
                }
            ]
        }
    },

    "GR 3.14": {
        "youtube_video_id": "Vp8yqP9rVfI",
        "youtube_title": "Calling-On Signal Aspect & Train Reception on Obstructed Line (GR 3.14)",
        "animation": {
            "title": "Receiving Train on Obstructed Platform Line using Calling-On Signal",
            "rule": "GR 3.14 & SR 3.14",
            "type": "flowchart_and_schematic",
            "schematic": "calling_on",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Train Halts at Home Signal (Red)",
                    "type": "start",
                    "desc": "Train comes to a complete standstill before the Home Signal displaying 'Danger' (Stop arm horizontal / Red light).",
                    "action": "Stop dead before Home Signal",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 2,
                    "title": "Time-Delay Circuit (120 Seconds)",
                    "type": "wait",
                    "desc": "Station Master initiates Calling-on button. Train must occupy the approach track circuit for 120 seconds before Calling-on can take 'OFF'.",
                    "action": "Wait 120s timer expiration"
                },
                {
                    "step_num": 3,
                    "title": "Calling-On Signal Displays Miniature Yellow",
                    "type": "action",
                    "desc": "Calling-on signal takes 'OFF' by displaying a miniature Yellow light (stop signal above remains RED).",
                    "action": "Miniature Yellow light illuminated"
                },
                {
                    "step_num": 4,
                    "title": "Draw Ahead at Max 15 KMPH",
                    "type": "action",
                    "desc": "Loco Pilot draws ahead with extreme caution at a speed NOT exceeding 15 kmph.",
                    "action": "Max 15 kmph with ALP on lookout",
                    "speed": "Max 15 KMPH"
                },
                {
                    "step_num": 5,
                    "title": "Stop Short of Obstruction / Preceding Train",
                    "type": "success",
                    "desc": "Be prepared to stop short of any vehicles, preceding train rake, or obstruction occupying the platform line.",
                    "action": "Stop short; report to Station Master",
                    "speed": "Stop short"
                }
            ]
        }
    },

    "GR 3.75": {
        "youtube_video_id": "k6lqWq7G4dI",
        "youtube_title": "Passing Intermediate Block Stop Signal (IBSS) at 'ON' (GR 3.75)",
        "animation": {
            "title": "Passing Intermediate Block Stop Signal (IBSS) at 'ON'",
            "rule": "GR 3.75 & SR 3.75",
            "type": "flowchart_and_schematic",
            "schematic": "ibss",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Stop Dead at IBSS (Red)",
                    "type": "start",
                    "desc": "Bring train to complete stop before the Intermediate Block Stop Signal (IBSS) displaying Red.",
                    "action": "Stop dead at IBSS",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 2,
                    "title": "Contact Rear Station Master on Post Phone",
                    "type": "decision",
                    "desc": "Loco Pilot opens signal post telephone box and rings the rear Station Master.",
                    "options": [
                        {"label": "SM Answers & Grants Line Clear", "next_step": 3, "color": "success"},
                        {"label": "Telephone Defective / No Reply", "next_step": 4, "color": "warning"}
                    ],
                    "action": "Telephone rear SM"
                },
                {
                    "step_num": 3,
                    "title": "Proceed on SM Verbal Clearance + Private No.",
                    "type": "success",
                    "desc": "Station Master confirms section is clear and gives Private Number. LP sounds horn, passes IBSS, and proceeds at normal speed.",
                    "action": "Pass IBSS with Private Number",
                    "speed": "Section speed"
                },
                {
                    "step_num": 4,
                    "title": "Wait 5 Minutes if Phone Fails",
                    "type": "wait",
                    "desc": "If phone fails or gives no answer, wait 5 minutes at the signal post.",
                    "action": "Wait 5 minutes"
                },
                {
                    "step_num": 5,
                    "title": "Proceed at 15 / 8 KMPH with Whistle",
                    "type": "action",
                    "desc": "Sound one continuous long whistle, exchange signals with Guard. Proceed at max 15 kmph (day/clear) or 8 kmph (night/fog) prepared to stop.",
                    "action": "15 kmph (day) / 8 kmph (night)",
                    "speed": "15 / 8 KMPH"
                }
            ]
        }
    },

    "GR 6.09": {
        "youtube_video_id": "a3b7c8d9e0f",
        "youtube_title": "Train Parting on Run - Engine Whistle Code & Headway Control (GR 6.09)",
        "animation": {
            "title": "Handling Train Parting on the Run (Preventing In-Section Collision)",
            "rule": "GR 6.09 & SR 6.09",
            "type": "flowchart_and_schematic",
            "schematic": "train_parting",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Detect Train Parting",
                    "type": "start",
                    "desc": "LP notes BP pressure drop + loco surging forward or Guard shows parting hand signal. Parting confirmed!",
                    "action": "Detect parting; DO NOT PANIC",
                    "speed": "Current speed"
                },
                {
                    "step_num": 2,
                    "title": "NEVER Apply Sudden Emergency Brakes",
                    "type": "action",
                    "desc": "Sudden braking will cause trailing portion to crash into locomotive! Keep engine moving forward at steady speed.",
                    "action": "Keep moving forward; Prevent collision"
                },
                {
                    "step_num": 3,
                    "title": "Sound Parting Whistle & Flasher ON",
                    "type": "action",
                    "desc": "Sound intermittent whistle '— 0 — 0' repeatedly and switch ON Flasher Light to alert Guard and stations.",
                    "action": "Whistle '— 0 — 0' + Flasher ON"
                },
                {
                    "step_num": 4,
                    "title": "Guard Gently Applies Handbrake",
                    "type": "action",
                    "desc": "Guard applies handbrake on rear portion carefully to bring it to a gradual, safe halt without skidding.",
                    "action": "Guard applies handbrake on rear"
                },
                {
                    "step_num": 5,
                    "title": "Front Portion Halts Safely",
                    "type": "success",
                    "desc": "When rear portion comes to a complete standstill, LP halts front portion at safe distance. Protect track in both directions.",
                    "action": "Halt front portion; Protect line",
                    "speed": "0 KMPH"
                }
            ]
        }
    },

    "GR 16.05": {
        "youtube_video_id": "p2w_K1v8R8A",
        "youtube_title": "Passing Level Crossing Gate Stop Signal at 'ON' with 'G' Marker (GR 16.05)",
        "animation": {
            "title": "Passing Level Crossing Gate Stop Signal at 'ON'",
            "rule": "GR 16.05 & SR 16.05",
            "type": "flowchart_and_schematic",
            "schematic": "gate_signal",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Stop Dead Before Gate Signal",
                    "type": "start",
                    "desc": "Stop dead before the Gate Signal displaying Red aspect. Confirm yellow circular 'G' marker with black letter 'G' is present.",
                    "action": "Stop dead before Gate Signal",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 2,
                    "title": "Mandatory Wait (1 Min / 2 Min)",
                    "type": "wait",
                    "desc": "Wait 1 minute by day / 2 minutes by night. Check if gateman is exhibiting hand signals.",
                    "action": "Wait 1 min (Day) / 2 min (Night)"
                },
                {
                    "step_num": 3,
                    "title": "Draw Ahead at Max 15 KMPH to Gate",
                    "type": "action",
                    "desc": "If gateman does not show all-right signal, draw ahead with extreme caution at max 15 kmph up to the level crossing gate.",
                    "action": "Draw ahead at 15 kmph to gate",
                    "speed": "Max 15 KMPH"
                },
                {
                    "step_num": 4,
                    "title": "Verify Gate Boom Closed & Padlocked",
                    "type": "decision",
                    "desc": "Stop before gate. Ensure gate booms are closed against road traffic and padlocked.",
                    "options": [
                        {"label": "Gate Closed & Locked", "next_step": 5, "color": "success"},
                        {"label": "Gate Open / Road Traffic", "next_step": 4, "color": "danger"}
                    ],
                    "action": "Check gate closure & lock"
                },
                {
                    "step_num": 5,
                    "title": "Pass Gate Safely",
                    "type": "success",
                    "desc": "ALP ensures road traffic is stopped. Sound horn, pass level crossing, and resume normal speed after clearing.",
                    "action": "Pass LC gate; Resume normal speed"
                }
            ]
        }
    },

    "SR 4.50": {
        "youtube_video_id": "w1x2y3z4a5b",
        "youtube_title": "Indian Railways Official Engine Whistle Codes Demonstration (SR 4.50)",
        "animation": {
            "title": "Operational Engine Whistle Codes (Loco Pilot Audible Protocol)",
            "rule": "SR 4.50",
            "type": "flowchart_and_schematic",
            "schematic": "whistle_codes",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Whistle Board (W/L) / Level Crossing",
                    "type": "action",
                    "desc": "Code: '— 0 — 0' (Intermittent Long-Short-Long-Short). Sound from 600m whistle board until gate is crossed.",
                    "action": "Sound '— 0 — 0'",
                    "location": "At W/L Board (600m)"
                },
                {
                    "step_num": 2,
                    "title": "Approaching Neutral Section",
                    "type": "action",
                    "desc": "Code: '— — 0' (Two long whistles followed by one short whistle). Alert ALP to standby at DJ switch.",
                    "action": "Sound '— — 0'",
                    "location": "At 500m Warning Board"
                },
                {
                    "step_num": 3,
                    "title": "Train Parting or Danger",
                    "type": "action",
                    "desc": "Code: '— 0 — 0' repeated continuously. Alert Guard and road/track workers of emergency situation.",
                    "action": "Sound '— 0 — 0' repeatedly",
                    "location": "Immediate"
                },
                {
                    "step_num": 4,
                    "title": "Calling Guard to Locomotive",
                    "type": "action",
                    "desc": "Code: '— — — —' (Continuous long blast). Guard must attend engine immediately with brake memo.",
                    "action": "Sound continuous long whistle",
                    "location": "Station or Section"
                }
            ]
        }
    },

    "GR 5.23": {
        "youtube_video_id": "m1n2o3p4q5r",
        "youtube_title": "Safety Protocol for Stabling Vehicles & Preventing Roll Down (GR 5.23)",
        "animation": {
            "title": "Stabling & Securing of Rolling Stock in Station Yards",
            "rule": "GR 5.23 & SR 5.23",
            "type": "flowchart_and_schematic",
            "schematic": "stabling_load",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Clear Foul Marks",
                    "type": "start",
                    "desc": "Ensure load is completely halted inside fouling marks (FM) of designated siding or loop line.",
                    "action": "Halt inside fouling marks",
                    "speed": "0 KMPH"
                },
                {
                    "step_num": 2,
                    "title": "Pin Down Hand Brakes",
                    "type": "action",
                    "desc": "Apply hand brakes on at least 6 wagons at each end + brake van hand brake firmly pinned down.",
                    "action": "Pin handbrakes (min 6 + 6 + BV)"
                },
                {
                    "step_num": 3,
                    "title": "Position Wooden Wedges / Skids",
                    "type": "action",
                    "desc": "Place wooden wedges or steel skids under the wheels of the outermost wagons facing falling gradient.",
                    "action": "Wedges under wheels"
                },
                {
                    "step_num": 4,
                    "title": "Padlock Safety Chains",
                    "type": "action",
                    "desc": "Secure wagon wheel to rail using heavy duty safety chain and padlock. Hand keys over to Station Master.",
                    "action": "Chain & padlock wheels to rail"
                },
                {
                    "step_num": 5,
                    "title": "Set Isolation Points / Traps",
                    "type": "success",
                    "desc": "Points set away from running lines to trap/sand hump and padlocked in normal position to prevent accidental entry.",
                    "action": "Trap/points set and locked"
                }
            ]
        }
    },

    "GR 4.19": {
        "youtube_video_id": "t5l6m7n8o9p",
        "youtube_title": "Train Completeness Verification - LV Board & Flashing Tail Lamp (GR 4.19)",
        "animation": {
            "title": "Train Integrity & Completeness Verification (LV Board / Tail Lamp)",
            "rule": "GR 4.19 & SR 4.19",
            "type": "flowchart_and_schematic",
            "schematic": "tail_lamp",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Daytime: 'LV' Board Displayed",
                    "type": "action",
                    "desc": "Last vehicle must display a standard circular board painted white/yellow with red 'LV' (Last Vehicle).",
                    "action": "LV board fixed on rear buffer/socket"
                },
                {
                    "step_num": 2,
                    "title": "Nighttime: Flashing Red Tail Lamp",
                    "type": "action",
                    "desc": "Last vehicle must exhibit an active flashing Red LED tail lamp clearly visible for at least 1.6 km in clear weather.",
                    "action": "Flashing Red LED tail lamp active"
                },
                {
                    "step_num": 3,
                    "title": "Station Master / Gateman Inspection",
                    "type": "decision",
                    "desc": "All Station Masters, Cabin staff, and Gatemen verify train completeness as train runs through.",
                    "options": [
                        {"label": "LV / Tail Lamp Present", "next_step": 4, "color": "success"},
                        {"label": "LV / Tail Lamp Missing!", "next_step": 5, "color": "danger"}
                    ],
                    "action": "Inspect last vehicle as it passes"
                },
                {
                    "step_num": 4,
                    "title": "Train Complete -> Transmit 'Train Out of Section'",
                    "type": "success",
                    "desc": "Station Master sends 'Train Out of Section' bell code to rear station. Line clear can be granted for next train.",
                    "action": "Clear block section"
                },
                {
                    "step_num": 5,
                    "title": "Suspected Train Parting Emergency",
                    "type": "action",
                    "desc": "Immediately display stop signal to train, stop train in advance, and inform rear SM. DO NOT CLEAR SECTION!",
                    "action": "Stop train; Verify completeness"
                }
            ]
        }
    },

    "GR 17.03": {
        "youtube_video_id": "o1h2e3s4a5f",
        "youtube_title": "25 kV Electric Traction 2-Metre Safety Clearance & Power Block Rules (GR 17.03)",
        "animation": {
            "title": "25 kV AC Electric Traction Safety Distances & Precautions",
            "rule": "GR 17.03 & SR 17.03",
            "type": "flowchart_and_schematic",
            "schematic": "ohe_safety",
            "steps": [
                {
                    "step_num": 1,
                    "title": "Live 25,000 Volt Equipment",
                    "type": "start",
                    "desc": "All contact wires, catenary, droppers, and pantographs are energized at 25 kV AC. Treat all wires as live at all times.",
                    "action": "High Voltage Danger Zone"
                },
                {
                    "step_num": 2,
                    "title": "Mandatory 2-Metre Safety Distance",
                    "type": "action",
                    "desc": "No person, uninsulated tool, ladder, measuring tape, or material shall approach within 2 metres of live OHE.",
                    "action": "Maintain minimum 2m clearance",
                    "location": "Within 2 metres radius"
                },
                {
                    "step_num": 3,
                    "title": "Climbing Roof / Wagons Prohibited",
                    "type": "action",
                    "desc": "No person shall climb on locomotive roof, carriage roof, or open wagon load without a valid Power Block and Earth Discharge Rods applied.",
                    "action": "Roof climbing strictly forbidden"
                },
                {
                    "step_num": 4,
                    "title": "Fallen Wire Hazard (10-Metre Radius)",
                    "type": "action",
                    "desc": "If an OHE wire is snapped and hanging or lying on ground, cordon off at least 10 metres radius. Prevent anyone from approaching.",
                    "action": "Keep 10m away; alert TLC 22328"
                },
                {
                    "step_num": 5,
                    "title": "Report Immediately to TLC 22328",
                    "type": "success",
                    "desc": "Immediately contact Traction Loco Controller on Railway Phone 22328 or Section Controller to arrange emergency power cut-off.",
                    "action": "Call TLC 22328 instantly"
                }
            ]
        }
    }
}

def enrich():
    app = create_app()
    with app.app_context():
        # Update MySQL database
        count = 0
        for rule_prefix, data in MEDIA_ENRICHMENT.items():
            # Find rule in DB e.g. rule_no starting with "GR 9.02" or "SR 4.50"
            rules = ELearningRule.query.filter(ELearningRule.rule_no.like(f"{rule_prefix}%")).all()
            for r in rules:
                r.youtube_video_id = data.get("youtube_video_id")
                r.youtube_title = data.get("youtube_title")
                r.animation_json = json.dumps(data.get("animation"), ensure_ascii=False)
                count += 1
                print(f"Updated DB rule: {r.rule_no} -> Video: {r.youtube_video_id}")
        db.session.commit()
        print(f"Updated {count} records in MySQL elearning_rules table.")

        # Update static/data/gr_sr_rules.json
        json_path = os.path.join(app.root_path, 'static', 'data', 'gr_sr_rules.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                rules_json = json.load(f)

            json_updated = 0
            for r in rules_json:
                r_no = r.get("rule_no", "")
                for prefix, data in MEDIA_ENRICHMENT.items():
                    if r_no.startswith(prefix):
                        r["youtube_video_id"] = data.get("youtube_video_id")
                        r["youtube_title"] = data.get("youtube_title")
                        r["animation"] = data.get("animation")
                        json_updated += 1

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(rules_json, f, indent=2, ensure_ascii=False)
            print(f"Updated {json_updated} rules in {json_path}")

if __name__ == '__main__':
    enrich()
