# Electric Operation Department, Howrah Division (Eastern Railway)
## Site & Web Application Portal

An end-to-end web portal and operational management system built for the **Electric Operation Department, Howrah Division, Eastern Railway**.

---

### 1. Hierarchy & Roles

```
                      ┌─────────────────────────────┐
                      │       Sr. DEE(OP)/HWH       │ (Branch Officer)
                      └──────────────┬──────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
            ┌────────┴────────┐             ┌────────┴────────┐
            │   AEE(OP)/HWH   │             │   AME(P)/HWH    │
            └────────┬────────┘             └────────┬────────┘
                     │                               │
                     └───────────────┬───────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         │                  11 Running Lobbies                   │
         │  (HWH, BWN, RPH, PKR, AZ, KWAE, NHT, BHP, TAK, KURV,  │
         │                         DKAE)                         │
         │              Chief Crew Controllers (CCC)             │
         └───────────────────────────┬───────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │     Chief Loco Inspectors     │
                     │             (CLI)             │
                     └───────────────┬───────────────┘
                                     │ (Nominated Squad / Footplate & Counselling)
                     ┌───────────────┴───────────────┐
                     │         Running Staff         │
                     │  (LPM, LPP, MMAN, LPG, LPS-I,  │
                     │      LPS-II, Sr. ALP, ALP)    │
                     └───────────────────────────────┘
```

---

### 2. Default Access Credentials

| Role | Username / Identifier | Default Password | Initial Security Behavior |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `12345` | Persistent security warning banner until password changed |
| **Officer** | `Sr. DEE(OP)/HWH` | `12345` | Persistent security warning banner until password changed |
| **Officer** | `AEE(OP)/HWH` | `12345` | Persistent security warning banner until password changed |
| **Officer** | `AME(P)/HWH` | `12345` | Persistent security warning banner until password changed |
| **Supervisor (CLI)** | `CLI_HWH_01` (or CLI ID) | `12345` | Persistent security warning banner until password changed |
| **Running Crew** | `9876543210` (Mobile No.) | `12345` | Persistent security warning banner until password changed |

*Running Staff can also self-register at `/auth/register`.*

---

### 3. Key Functional Highlights

1. **Public Information Portal**:
   - **Top Bar**: Live GPS-synchronized Indian Railway Standard Time Clock, Locomotive icon, Login status.
   - **Navigation Tabs**: Home, About, Sr. DEE(OP) Instructions, Notices & Results, Daily Safety Counselling, E-Learning (GR & SR, Troubleshooting, Operating Forms, Safety Quiz), Photo Gallery, Contact Us.
   - **Hero Carousel**: High-definition presentation of department operations and electric traction fleet.
   - **Notice Ticker**: Real-time marquee and dynamic list of circulars with `NEW` badges and PDF downloads.
   - **Officers' Desk ("Officers Say")**: Personalized safety guidance and photographs of Sr. DEE(OP), AEE(OP), and AME(P).
   - **11 Running Lobbies Directory**: Detailed contacts and CCC names for HWH, BWN, RPH, PKR, AZ, KWAE, NHT, BHP, TAK, KURV, and DKAE.

2. **Hierarchical Communication Workflow**:
   - Running staff can send queries/issues only to their nominated CLI.
   - The CLI has two options:
     - **Resolve directly** with technical guidance.
     - **Forward to Officers** (Sr. DEE/AEE/AME) with CLI recommendations.
   - Officers can send **direct messages** to any running staff or CLI.

3. **Electronic Assurance Register**:
   - Running staff have an **"Acknowledge (Read & Understood)"** button on safety notices and daily counselling topics in accordance with SR 2.03 and SR 4.30.

4. **Training & Competency Expiry Tracker**:
   - Color-coded badges for Refresher courses, Automatic Block System (6-month renewal), and Periodical Medical Examination (PME):
     - **Green**: Valid (>30 days remaining)
     - **Yellow**: Due soon (within 30 days)
     - **Red**: Overdue (Immediate safety alert)

5. **Bulk Excel Upload & Automatic Recognition**:
   - In Admin Console (`/admin/upload-excel`):
     - Upload Crew Excel (auto-activates accounts and maps to nominated CLI).
     - Upload CLI Excel.
     - Upload Training Excel.
     - Pre-formatted downloadable templates provided for all datasets.

---

### 4. Running the Application

Double-click `run_portal.bat` or run:
```bash
python app.py
```
Open your browser at: `http://localhost:5000`
