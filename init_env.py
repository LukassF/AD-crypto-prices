import shutil
import os

base_path = os.path.dirname(os.path.abspath(__file__))

env_example = os.path.join(base_path, ".env.example")
env_target = os.path.join(base_path, ".env")

print(f"[INFO] Initializing environment in: {base_path}")

if not os.path.exists(env_target):
    if os.path.exists(env_example):
        shutil.copy(env_example, env_target)
        print("[SUCCESS] Created .env from .env.example.")
    else:
        print(f"[ERROR] Could not find: {env_example}")
else:
    print("[SKIP] .env already exists.")
