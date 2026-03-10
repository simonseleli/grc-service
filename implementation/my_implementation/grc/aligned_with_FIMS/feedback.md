okay, but im so sorry, i hav two cases:

case 1: i did by partially following the guide:

i have create the record as:
{recommendation_id: "3dd05a5a-477f-4c53-948f-ba1eff743bd2", latest_progress: "30",…}
latest_progress
: 
"30"
next_review_date
: 
"2026-03-11"
recommendation_id
: 
"3dd05a5a-477f-4c53-948f-ba1eff743bd2"
reviewed_by
: 
"fb680f30-398b-4b86-865b-455a35c3c8d9"


response:
{success: true, data: {id: "2b1cb8bc-d932-40de-a6fc-fc6b56b04843",…},…}
data
: 
{id: "2b1cb8bc-d932-40de-a6fc-fc6b56b04843",…}
message
: 
"Implementation monitoring record created successfully"
success
: 
true

1. 
now, i click on view,  and click the update progress, and click send notification, and got No open review cycle. Call /review/ first to create a new cycle.

2. so i decide to click view, and then clicked Record Response button, and confirm to add the response, o i added as
Follow-Up Cycles (1)

clicked submit progress, and put 45, notes "Implementation Progress", and click sumit progress, 

payload:
{implementation_progress: 45, progress_notes: "Implementation Progress"}
implementation_progress
: 
45
progress_notes
: 
"Implementation Progress"


response:
{success: true,…}
data
: 
{id: "6ca9a3aa-f94e-4046-9c63-5fae8a8e4b01", cycle_number: 1, status: "submitted", notified_at: null,…}
message
: 
"Response submitted successfully."
success
: 
true


again, i clik the Verify Response, and put notes as "Notes"
payload:
{verdict: "verified", verification_notes: "Notes"}
verdict
: 
"verified"
verification_notes
: 
"Notes"


reposne:
preview:
{success: true,…}
data
: 
{id: "6ca9a3aa-f94e-4046-9c63-5fae8a8e4b01", cycle_number: 1, status: "verified", notified_at: null,…}
message
: 
"Response verified. Header latest_progress updated."
success
: 
true

now, i go back to the table, and see the startus is chanegd to "Responded"
is this correct flow??

and  again:
i can repeat this steps by clicking the view, add Record Response and fill the percentage and coonfirms and real the system takes the one with maximam,


but i again tried (with the status Responded), i click on update progess, then i see the send notification, 
and got:
{success: false,…}
error
: 
{message: "No open review cycle. Call /review/ first to create a new cycle.", code: "NO_OPEN_CYCLE"}
code
: 
"NO_OPEN_CYCLE"
message
: 
"No open review cycle. Call /review/ first to create a new cycle."
success
: 
false

so i tried agian to go on view, and add the Record Response so i have now three cycles, and cofirm it and fill its percantage and save now when i come and click the send notification, still etting the No open review cycle. Call /review/ first to create a new cycle.



case 2:
i really followd the guide:
by following your approach on the notes:
i deleted the one, and then,
i created as 
{recommendation_id: "3dd05a5a-477f-4c53-948f-ba1eff743bd2", latest_progress: "25",…}
latest_progress
: 
"25"
next_review_date
: 
"2026-03-11"
recommendation_id
: 
"3dd05a5a-477f-4c53-948f-ba1eff743bd2"
reviewed_by
: 
"fb680f30-398b-4b86-865b-455a35c3c8d9"

now as the document says:
### Step 2 — Open the First Review Cycle

so i did:
1. Find the monitoring record in the table
2. Click the **👁 View** (eye icon) → the Detail Dialog opens
3. Click **Record Response**
4. A small panel appears — click **Confirm Create Cycle**

**Expected result:** A follow-up cycle (Cycle 1) appears in the dialog with status `Pending`.

so from here, im able to do anything for i see this:
Cycle 1
Pending
0.00%
Submit Progress

when i click the submit progress i can fill the percenatage, but according to notes, 

so i close the dialog and proceed with ### Step 3 — Notify the Auditee

so here i did,

i go to the table, and on the item i click.

2. Find your monitoring record → click **Progress Update**
3. The action shown is **Notify Auditee** (because `notification_sent_at` is currently null)
4. Click it


and see this:

{success: true, data: {id: "0bfcf616-26c9-48ad-8b6e-d0d7423d5122",…},…}
data
: 
{id: "0bfcf616-26c9-48ad-8b6e-d0d7423d5122",…}
auditee_responded_at
: 
null
created_at
: 
"2026-03-10T18:02:08.251461+03:00"
days_until_deadline
: 
6
escalated
: 
false
follow_up_responses
: 
[{id: "e2f5217f-8285-42ab-8438-64e6d4de71c9", cycle_number: 1, status: "pending",…}]
id
: 
"0bfcf616-26c9-48ad-8b6e-d0d7423d5122"
is_active
: 
true
is_overdue
: 
false
last_review_date
: 
null
latest_progress
: 
"25.00"
next_review_date
: 
"2026-03-11"
notification_sent_at
: 
"2026-03-10T18:08:01.664368+03:00"
recommendation
: 
{id: "3dd05a5a-477f-4c53-948f-ba1eff743bd2", reference_number: "REC-FND-ENG-2026-001-001-002",…}
response_deadline
: 
"2026-03-17T18:08:01.664368+03:00"
reviewed_by
: 
"fb680f30-398b-4b86-865b-455a35c3c8d9"
status
: 
"active"
updated_at
: 
"2026-03-10T18:02:08.251491+03:00"
message
: 
"Auditee notified (cycle 1). Response deadline: 2026-03-17 15:08"
success
: 
true




now, to this""**Expected result:**
- `notification_sent_at` is set on the cycle
- `response_deadline` is set to `notified_at + 5 business days`
- The Progress Update button will now show **Record Review** instead of **Notify Auditee**""

 i was still see the button named update progress, and when i click it, it opens:
 Record Review
Record progress notes and set the next review date for this monitoring item.

Implementation Progress (%) *
25.00
Progress Notes
Describe the implementation progress...
Next Review Date
mm/dd/yyyy
Cancel
Save Review


so i didnt see the Notify Auditee buttoon there, 


so i go back on the table and proceed wih next step, 
### Step 4 — Auditee Submits Progress

so i did

i did click the view button, and takes me to,
Cycle 1
Pending
0.00%
Deadline: 3/17/2026
Submit Progress


i did this exactly,
This is the auditee recording how far implementation has progressed.

1. Click the **👁 View** (eye icon) on the monitoring record → Detail Dialog opens
2. Find **Cycle 1** in the Follow-Up Cycles section (status shows `Pending`)
3. Click **Submit Progress** on that cycle card
4. Fill in:
   - **Implementation Progress (%)**: `40`
   - **Response Notes** *(optional)*: `Initial procurement process started. RFQ issued to 3 vendors. Vendor evaluation in progress.`
5. Click **Submit Progress**

ans sees:

{implementation_progress: 40,…}
implementation_progress
: 
40
progress_notes
: 
"Initial procurement process started. RFQ issued to 3 vendors. Vendor evaluation in progress."


and ofcourse these appeared: Submitted: 3/10/2026
Deadline: 3/17/2026

now



on stp 5, i did the same as:

### Step 5 — Auditor Verifies the Response

1. Stay in the Detail Dialog (or re-open it via **View**)
2. Find Cycle 1 — it now shows status `Submitted` and a **Verify Response** button
3. Click **Verify Response**
4. Optionally enter **Verification Notes**: `Progress confirmed. Vendor evaluation documentation reviewed. 40% progress accepted.`
5. Click **Confirm Verify** 

**Expected result (if Verified):**
- Cycle 1 status → `Verified`
- Header `latest_progress` updated to `40%` (synced from the cycle)


and now this was the summary of the cycle 1:Cycle 1
Verified


Cycle 1
Verified
40.00%
Initial procurement process started. RFQ issued to 3 vendors. Vendor evaluation in progress.

Submitted: 3/10/2026
Verified 3/10/2026
Deadline: 3/17/2026
Verification notes: Progress confirmed. Vendor evaluation documentation reviewed. 40% progress accepted.





so, between these, which on is correct, and where there is bugs or corrections?