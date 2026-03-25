i started testing, so i logged in as admin:admin@fcc.go.tz

i entered:http://localhost:3001/service/grc/risk-champions

1. and when i click create new risk champion,

Nominate Risk Champion
Nominate a staff member as risk champion for a directorate/unit/zone.


i got


{
    "success": false,
    "error": {
        "message": "role_code must be one of: ['audit_committee', 'auditee', 'chief_internal_auditor', 'internal_auditor', 'management']",
        "code": "INVALID_ROLE_CODE"
    }
}


2. on the same create dialog, when i click the 
a. Nominee *
Select nominee… and
b. Directorate / Unit / Zone *
Select directorate…

 i got nothing,
 

- is it correct?


3. in Create Risk Assessment Sheet

still i get the sane error 

{
    "success": false,
    "error": {
        "message": "role_code must be one of: ['audit_committee', 'auditee', 'chief_internal_auditor', 'internal_auditor', 'management']",
        "code": "INVALID_ROLE_CODE"
    }
}


its header:
Request URL
http://localhost:8080/api/v1/grc/audit/lookups/users/?role_code=risk_champion
Request Method
GET
Status Code
400 Bad Request
Remote Address
[::1]:8080
Referrer Policy
strict-origin-when-cross-origin





4. i tried to log in as RISK users like: riskchampion@fcc.go.tz
password: Pass@1234 and got 
Invalid credentials. Please check your email and password.

Failed attempts: 2 / 3
One more attempt will lock your account



so verify if these users have been created and can log in, both RISK and LEGAL users, 
if they dont exists, then see the file grc-service/implementation/my_implementation/grc/notes/grc_notes.md for reference how to create them and assigning the peremissions