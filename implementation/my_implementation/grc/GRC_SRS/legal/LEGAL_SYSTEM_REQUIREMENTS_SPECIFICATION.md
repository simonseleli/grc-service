**SYSTEM REQUIREMENTS SPECIFICATION (SRS)**

**Legal Services Module**

**1. Introduction**

**1.1 Purpose**

This document defines the system requirements for the GRC Legal Services
module. The module manages governance meetings, decisions, directives,
and litigation matters (FCC as plaintiff and as defendant). It provides
a unified platform for tracking submissions for determination, meeting
lifecycles, litigation cases, and public registers.

**1.2 Scope**

-   **Meeting Governance:** Full lifecycle of meetings (creation, agenda
    building from determination submissions, participant management,
    conflict of interest, quorum, minutes, resolutions, directives).

-   **Governance Structures:** Management of committees, governing
    bodies, members, and secretaries.

-   **Determinations & Approvals:** Unified submission process for
    documents requiring formal decision by Management, Commission, or
    Committee.

-   **Litigation -- FCC Sued:** End-to-end management of cases where FCC
    is defendant.

-   **Litigation -- FCC Suing:** End-to-end management of cases where
    FCC is plaintiff.

-   **Public Register:** Management and publication of finalised
    decisions.

**2. Stakeholders and User Roles**

  -----------------------------------------------------------------------
  **Role**                 **Description**
  ------------------------ ----------------------------------------------
  System Administrator     Configures master data (committee types,
                           governing bodies, members). Manages access
                           rights and system settings.

  Secretariat / Governance Creates meeting packs, schedules meetings,
  Officer                  records minutes, resolutions, and directives.
                           Publishes public decisions. Often acts as
                           **Secretary** of a governing body.

  Management Member /      Consumes meeting packs, participates in
  Commissioner / Committee meetings, receives directives, reviews and
  Member                   approves items. Can declare conflicts of
                           interest.

  Legal Officer            Manages litigation cases (both FCC sued and
                           suing). Handles filings, hearings, judgments,
                           settlements, tasks, and financials.

  Legal Manager            Supervises Legal Officers, reviews and
                           recommends filings to DG, manages case
                           assignments, initiates closures.

  Director General (DG)    Reviews litigation cases, issues directives,
                           approves filings, settlements, and case
                           closures. Decides on appeals.

  Department User          Creates submissions for determination (breach
  (Submitter)              reports, etc.).

  Invitee (Internal Staff) May be invited to meetings as non-members; can
                           view agendas and directives.

  Public / External        Access public register of decisions
  Stakeholder              (Integration with FCC CRM).
  -----------------------------------------------------------------------

**3. Overall System Overview**

**3.1 High-Level Functional Overview**

The Legal Services module comprises the following functional areas:

1.  **Meeting Governance Module** -- Manages meeting lifecycle, agendas,
    participants, quorum, minutes, resolutions, and directives.

2.  **Governance Structure & Participants Module** -- Maintains
    committees, governing bodies, members, and secretaries.

3.  **Determinations & Approvals Module** -- Unified submission process
    for items requiring formal decision.

4.  **Litigation -- FCC Sued Module** -- Manages cases where FCC is
    defendant.

5.  **Litigation -- FCC Suing Module** -- Manages cases where FCC is
    plaintiff.

6.  **Public Register Module** -- Manages and publishes decisions.

Cross-cutting capabilities include document management, audit logging,
notifications, search/filtering, and integration with Corporate Service,
Documents & Records Management, and IAM microservices.

**4. Functional Requirements**

**4.3 Determinations & Approvals Module (FCC\_ SBP_LS_TB_01)**

  ---------------------------------------------------------------------------
  **ID**      **Requirement Description**                      **Actor(s)**
  ----------- ------------------------------------------------ --------------
  FR-DET-01   Any user can create **Submission for             Department
              Determination**.                                 User

  FR-DET-02   Submission status includes Submitted, Under      System
              Review, Deferred, Approved, Rejected.            

  FR-DET-03   Submissions become available for meeting agenda  System
              selection.                                       

  FR-DET-04   Originator may update or withdraw submission     Originator
              before agenda inclusion.                         

  FR-DET-05   Determination outcome recorded after meeting.    System
  ---------------------------------------------------------------------------

**4.1 Meeting Governance Module**

**4.1.1 Meeting Lifecycle**

  ---------------------------------------------------------------------------------
  **ID**      **Requirement Description**                            **Actor(s)**
  ----------- ------------------------------------------------------ --------------
  FR-MTG-01   The system shall allow a Secretary to create a meeting Secretary
              with the following fields: title (predefined types,    
              e.g., Commission Meeting, Audit Committee Meeting),    
              meeting number (auto-generated), location, mode        
              (Physical/Virtual/Hybrid), venue/meeting link, start   
              and end dates/times, type                              
              (Ordinary/Extraordinary/Special), governing body       
              (selected from bodies the secretary is assigned to),   
              agenda summary, and status (initially **Draft**).      

  FR-MTG-02   Meeting numbers shall be auto-generated using          System
              type-specific prefixes (e.g., CM for Commission        
              Meeting, ACM for Audit Committee Meeting) and either   
              an endless sequence (e.g., CM-001) or a financial-year 
              format (e.g., CM/2025-2026/001) based on the governing 
              body\'s numbering preference.                          

  FR-MTG-03   The Secretary can select agenda items from             Secretary
              **Submissions for Determination** (see Module 3) that  
              are targeted to the meeting's governing body. Selected 
              items become the meeting agenda.                       

  FR-MTG-04   The system shall automatically populate a **Matters    System
              Arising** section with all unresolved directives from  
              previous meetings of the same governing body.          

  FR-MTG-05   During the meeting, the Secretary can add new          Secretary
              directives to any agenda item or matters arising item, 
              specifying description, assignee (person/unit),        
              priority (Critical/High/Medium/Low), and due date.     

  FR-MTG-06   The Secretary can finally close a directive in Matters Secretary
              Arising, which removes it from future meetings. Final  
              closure requires a completion summary and optional     
              evidence.                                              

  FR-MTG-07   The system shall automatically populate the            System
              **Members** section of a meeting with all members of   
              the selected governing body.                           

  FR-MTG-08   The Secretary can invite additional internal staff via Secretary
              the **Invitees** section.                              

  FR-MTG-09   After the meeting is registered, the system sends      System
              invitations to all members and invitees.               

  FR-MTG-10   Quorum is defined as at least **51% of members**       System
              accepting the invitation.                              

  FR-MTG-11   If quorum is not met, the Secretary can reschedule the Secretary
              meeting.                                               

  FR-MTG-12   Members may declare **conflict of interest** on        Member
              specific agenda items.                                 

  FR-MTG-13   The Secretary can start the meeting only if quorum is  Secretary
              met.                                                   

  FR-MTG-14   The Secretary can postpone the meeting if it continues Secretary
              beyond the original end time.                          

  FR-MTG-15   The Secretary can close the meeting when business is   Secretary
              concluded.                                             

  FR-MTG-16   The system maintains a full **Audit Tab** logging      System
              actions with user and timestamp.                       
  ---------------------------------------------------------------------------------

**4.1.2 Minutes and Resolutions**

  --------------------------------------------------------------------------
  **ID**      **Requirement Description**                     **Actor(s)**
  ----------- ----------------------------------------------- --------------
  FR-MTG-17   The Secretary can add minutes during or after   Secretary
              the meeting including attachments.              

  FR-MTG-18   Minutes are submitted for approval to governing Secretary,
              body members who participated.                  Members

  FR-MTG-19   All formal decisions are automatically captured System
              in the **Resolutions Register**.                

  FR-MTG-20   Resolutions are visible only to invited         System
              participants and are searchable.                
  --------------------------------------------------------------------------

**4.1.3 Directives Management**

  --------------------------------------------------------------------------------
  **ID**      **Requirement Description**                           **Actor(s)**
  ----------- ----------------------------------------------------- --------------
  FR-MTG-21   Directives include ID, meeting reference,             System
              description, category, priority, assigned             
              organisation/department, assigned member, due date,   
              status, completion summary, completion date, and      
              evidence document.                                    

  FR-MTG-22   Only the assigned person can perform initial closure. Assigned User

  FR-MTG-23   Final closure is done by the Secretary in **Matters   Secretary
              Arising** in a later meeting.                         

  FR-MTG-24   All invitees can view directives in read-only mode.   All Invitees
  --------------------------------------------------------------------------------

**4.2 Governance Structure & Participants Module**

  ---------------------------------------------------------------------------
  **ID**      **Requirement Description**                     **Actor(s)**
  ----------- ----------------------------------------------- ---------------
  FR-GOV-01   Configure **Committee Types**.                  Administrator

  FR-GOV-02   Manage **Governing Bodies**.                    Administrator

  FR-GOV-03   Manage **Committee Members**.                   Administrator

  FR-GOV-04   Manage **Management Members**.                  Administrator

  FR-GOV-05   Assign users as **Secretary** to multiple       Administrator
              governing bodies.                               
  ---------------------------------------------------------------------------

**4.4 Litigation -- FCC Sued Module (FCC\_ SBP_LS_TB_02 conjunction with
FCC\_ SBP_LS_TB_04)**

**4.4.1 Dashboard and Case List**

  -----------------------------------------------------------------------------
  **ID**       **Requirement Description**                       **Actor(s)**
  ------------ ------------------------------------------------- --------------
  FR-SUED-01   Dashboard displays KPIs: Total Cases Filed, Cases All authorised
               Won/Loss Ratio, Cases on Appeal, High Risk Cases, users
               Active Cases, Pending DG Review.                  

  FR-SUED-02   Case list includes columns: Case Ref No,          All authorised
               Respondent, Case Type, Court, Claim Amount,       users
               Stage, Status, Risk, Next Hearing, Actions.       

  FR-SUED-03   Users can filter case list and perform global     All authorised
               search.                                           users
  -----------------------------------------------------------------------------

**4.4.2 Case Registration**

  -----------------------------------------------------------------------------
  **ID**       **Requirement Description**                      **Actor(s)**
  ------------ ------------------------------------------------ ---------------
  FR-SUED-04   Registry Officer,Legal Officer or Legal Manager  Legal Officer,
               can register a new case with fields including    Registry
               Court Registry, Case Number, Service Date,       OfficerLegal
               Applicant Name, Advocate, Claim Amount, Nature   Manager
               of Claim, Department Affected, Urgency Level,    
               Risk Level, and documents served.                

  FR-SUED-05   System auto-generates Case Reference Number      System
               FCC/SUED/YYYY/NNN.                               
  -----------------------------------------------------------------------------

**4.4.3 DG Review and Directive**

  ------------------------------------------------------------------------------
  **ID**       **Requirement Description**                        **Actor(s)**
  ------------ -------------------------------------------------- --------------
  FR-SUED-06   DG reviews the case and may issue directives.      DG

  FR-SUED-07   When directive issued case moves to **Directive    System
               Issued** stage.                                    
  ------------------------------------------------------------------------------

**4.4.4 Case Handling**

  --------------------------------------------------------------------------
  **ID**       **Requirement Description**             **Actor(s)**
  ------------ --------------------------------------- ---------------------
  FR-SUED-08   Legal Manager assigns Legal Officers.   Legal Manager

  FR-SUED-09   Legal Officer creates filings under     Legal Officer
               **Court Filings** tab.                  

  FR-SUED-10   Filing approval workflow: Legal Officer Legal Officer, Legal
               → Legal Manager → DG.                   Manager, DG

  FR-SUED-11   Notifications sent at each approval     System
               stage.                                  

  FR-SUED-12   Respondent documents recorded under     Legal Officer
               **Responses** tab.                      

  FR-SUED-13   Hearings recorded with hearing date,    Legal Officer
               judge, notes and reports.               

  FR-SUED-14   Settlement details recorded under       Legal Officer, Legal
               **Settlement** tab.                     Manager, DG

  FR-SUED-15   Judgment recorded under **Judgment**    Legal Officer
               tab.                                    

  FR-SUED-16   DG decides whether to accept judgment   Legal Manager, DG
               or appeal.                              

  FR-SUED-17   Finance tab records costs and           Legal Officer, Legal
               recoveries.                             Manager

  FR-SUED-18   Tasks tab lists system and manual       All
               tasks.                                  

  FR-SUED-19   Case folder link provided to Documents  All
               Microservice.                           

  FR-SUED-20   Report tab shows chronological          All
               timeline.                               

  FR-SUED-21   Activity log records every action.      System
  --------------------------------------------------------------------------

**4.4.5 Case Closure**

  -------------------------------------------------------------------------
  **ID**       **Requirement Description**                  **Actor(s)**
  ------------ -------------------------------------------- ---------------
  FR-SUED-22   Legal Manager initiates case closure subject Legal Manager,
               to DG approval.                              DG

  -------------------------------------------------------------------------

**4.4.6 Archiving**

  ---------------------------------------------------------------------------
  **ID**       **Requirement Description**                **Actor(s)**
  ------------ ------------------------------------------ -------------------
  FR-SUED-23   Closed cases may be archived manually or   Administrator,
               automatically after a configurable period. Legal Manager

  ---------------------------------------------------------------------------

**4.5 Litigation -- FCC Suing Module (FCC\_ SBP_LS_TB_03 conjunction
with FCC\_ SBP_LS_TB_04)**

**4.5.1 Dashboard and Case List**

  ------------------------------------------------------------------------------
  **ID**        **Requirement Description**                       **Actor(s)**
  ------------- ------------------------------------------------- --------------
  FR-SUING-01   Dashboard displays KPIs including Total Cases     All authorised
                Filed, Won/Loss Ratio, Cases on Appeal, High Risk users
                Cases, Active Cases, Pending DG Review,           
                Recoverable Amount, Recovered Amount.             

  FR-SUING-02   Case list columns include Case Ref No,            All authorised
                Respondent, Case Type, Court, Claim Amount,       users
                Stage, Status, Risk, Next Hearing, Actions.       
  ------------------------------------------------------------------------------

**4.5.2 Case Registration (Breach Reporting)**

  ---------------------------------------------------------------------------
  **ID**        **Requirement Description**               **Actor(s)**
  ------------- ----------------------------------------- -------------------
  FR-SUING-03   System provides **Breach Report Intake**  Department User,
                and **Full Breach Report** interfaces.    Legal Officer

  FR-SUING-04   Case reference number auto generated as   System
                FCC/SUING/YYYY/NNN.                       
  ---------------------------------------------------------------------------

**4.5.3 DG Review and Directive**

  -------------------------------------------------------------------------------
  **ID**        **Requirement Description**                        **Actor(s)**
  ------------- -------------------------------------------------- --------------
  FR-SUING-05   DG reviews the case and issues directive or marks  DG
                as reviewed.                                       

  FR-SUING-06   When directive issued case stage becomes           System
                **Directive Issued**.                              
  -------------------------------------------------------------------------------

**4.5.4 Case Handling**

  ---------------------------------------------------------------------------
  **ID**        **Requirement Description**                 **Actor(s)**
  ------------- ------------------------------------------- -----------------
  FR-SUING-07   Legal Manager assigns Legal Officers.       Legal Manager

  FR-SUING-08   Legal Officer creates filings with          Legal Officer
                plaintiff filing types.                     

  FR-SUING-09   Respondent documents recorded under         Legal Officer
                **Responses** tab.                          

  FR-SUING-10   Hearings handled same as FR-SUED-13.        Legal Officer

  FR-SUING-11   Settlement handling identical to            Legal Officer
                FR-SUED-14.                                 

  FR-SUING-12   Judgment recording identical to FR-SUED-15. Legal Officer

  FR-SUING-13   DG decides whether to appeal after          Legal Manager, DG
                judgment.                                   

  FR-SUING-14   Finance tab tracks costs and recoveries.    Legal Officer,
                                                            Legal Manager

  FR-SUING-15   Tasks, Case Folder, Report timeline,        All
                Activity Log same as FR-SUED-18 to          
                FR-SUED-21.                                 
  ---------------------------------------------------------------------------

**4.5.5 Case Closure and Archiving**

  --------------------------------------------------------------------------
  **ID**        **Requirement Description**            **Actor(s)**
  ------------- -------------------------------------- ---------------------
  FR-SUING-16   Case closure initiated by Legal        Legal Manager, DG
                Manager and approved by DG.            

  FR-SUING-17   Archiving follows same rules as        Administrator, Legal
                FR-SUED-23.                            Manager
  --------------------------------------------------------------------------

**6. Integration Points**

  -----------------------------------------------------------------------
  **Microservice**        **Purpose**
  ----------------------- -----------------------------------------------
  Corporate Service       Provides department lists and staff
                          information.

  Corporate Service       Provides Link to financial processes. Revenue
                          Collection and External Payment under Finance

  Documents and Records   Stores case documents and provides version
  Management              control.

  IAM                     Manages authentication and permissions.

  Work Orchestration      Interconnection of Processes from Different
                          Services, Notifications and Remainder
  -----------------------------------------------------------------------
