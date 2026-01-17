# startup_probe.py
import os, sys, pathlib
print("=== STARTUP PROBE ===")
print("CWD:", os.getcwd())
print("FILES_IN_CWD:", sorted(os.listdir("."))[:50])
print("PYTHONPATH:", sys.path[:5])
print("HAS_MAIN_PY:", os.path.exists("main.py"))
print("HAS_LOCAL_MAIN_PY:", os.path.exists("local_main.py"))
print("HAS_DEPLOY_PROOF:", any(n.startswith("DEPLOY_PROOF_") for n in os.listdir(".")))
try:
    if os.path.exists("amvera_sync_trigger.txt"):
        with open("amvera_sync_trigger.txt", "r", encoding="utf-8") as f:
            first = f.readline().strip()
        print("AMVERA_SYNC_TRIGGER_FIRST_LINE:", first)
except Exception as e:
    print("AMVERA_SYNC_TRIGGER_READ_ERROR:", repr(e))
print("=====================")
