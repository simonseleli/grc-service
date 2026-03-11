# GRC-Service Notes

These are some notes while dealing with **grc-service**.

---

## 1. How I do migrations

NOTE:
I usually run migrations without creating manual files. The workflow:

```bash
# Generate migrations
docker compose exec grc-service python manage.py makemigrations

# Apply migrations
docker compose exec grc-service python manage.py migrate

# Check applied migrations
docker compose exec grc-service python manage.py showmigrations core
```

## 2. How to log in via IAM service

a. Token creation example:
```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/iam/auth/login/ -H "Content-Type: application/json" -d '{"email":"admin@fcc.go.tz","password":"admin123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access','') or d.get('data',{}).get('access',''))") && echo "TOKEN=${TOKEN:0:40}..."


b, Login and accessing something example
curl -s -H "Authorization: Bearer $TOKEN"
"http://localhost:8006/api/v1/grc/lookups/fiscal-years/"
| jq '.data[:3] | map({id, year_code})'
```



## 3. get current user UUID

```bash
import json, base64
token='$TOKEN'
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
d = json.loads(base64.b64decode(payload))
print('user_id:', d.get('user_id',''))
```


unlocking admi account:

cd /home/simons/Coding/FIMS/iam-service && docker compose exec iam-service python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(email='admin@fcc.go.tz')
u.failed_login_attempts = 0
u.locked_until = None
u.save()
print('Unlocked:', u.email)
"




## 4. restarting grc service

Restarting grc-service:
docker compose restart grc-service 2>&1 | tail -3

or

docker compose restart grc-service && sleep 5 && echo "Restarted"



## 5. get running containers

just run: dps

(for i have already set the alias for this: alias dps='docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}\t{{.RunningFor}}"')




6. deleting audit reports:

cd /home/simons/Coding/FIMS/grc-service && docker compose exec grc-service python manage.py shell -c "
from apps.core.models.audit_entities import AuditReport
count = AuditReport.objects.count()
AuditReport.objects.all().delete()
print(f'Deleted {count} audit report(s). Remaining: {AuditReport.objects.count()}')
"

