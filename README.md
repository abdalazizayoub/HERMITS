# HERMITS
Hybrid Engine for Remediation, Monitoring &amp; IT Support

HERMITS is a submission for the Techbold track in the START Vienna Hackathon. The aim is to:
- Build a technician workspace that pulls assigned tickets from a mock Phoenix ERP, loads the affected customer system, connects over SSH, and diagnoses the incident.
- The AI may propose diagnostic and fix steps, but the technician must approve every system action. After validation, the workspace writes a precise activity log back to the ERP.
- The evaluation uses fresh systems your team has not seen before, so hard-coded fixes and unsafe broad commands will not hold up.

setup
docker, requirements, compose

run
compose

environment
docker

architecture
soon

assumptions
soon

troubleshooting
soon

1. GET  /api/tickets/                    → list all 5 tickets
2. GET  /api/tickets/{id}               → ticket detail + SSH info

3. POST /api/agent/ai/phase1            → Gemini generates 3 pillar validation 
                                           commands + KB pre-match
                                           (happens on ticket open)

4. POST /api/agent/recon                → SSH into VM, runs 13 read-only commands
                                           returns raw system state

5. POST /api/agent/ai/phase2            → Gemini analyses recon + KB + pillars
                                           returns 3 ranked hypotheses with fix steps

6. POST /api/agent/execute              → runs ONE approved command over SSH
                                           safety layer blocks hard-fails
                                           audit log records everything
                                           (repeat per approved step)

7. POST /api/agent/validate             → runs public-test.sh on VM
                                           returns pass/fail + output

8. POST /api/agent/ai/complete          → pillar before/after validation
                                           auto-drafts ERP activity
                                           writes KB entry for future tickets

9. POST /api/activities/submit          → submits activity to Phoenix ERP
                                           sets ticket status to DONE
