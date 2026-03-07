# GRC-Service Notes

These are some notes while dealing with **grc-service**.

---

## 1. How I do migrations

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






Restarting grc-service:
docker compose restart grc-service && sleep 5 && echo "Restarted"

or  

docker compose restart grc-service 2>&1 | tail -3

