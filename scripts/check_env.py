import os
import sys

required = [
    "SECRET_KEY",
    "JWT_SECRET_KEY", 
    "DATABASE_URL",
    "DATABASE_URL_SYNC",
    "ALLOWED_ORIGINS",
]

missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"ERROR: Missing environment variables: {missing}")
    sys.exit(1)

print("All required env vars present")
print(f"DATABASE_URL starts with: {os.environ.get('DATABASE_URL', '')[:30]}")
print(f"ALLOWED_ORIGINS: {os.environ.get('ALLOWED_ORIGINS', '')}")