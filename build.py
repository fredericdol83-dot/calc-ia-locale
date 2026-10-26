"""Fabrique dist/calc-ia-locale.oxt à partir du dossier extension/ : python3 build.py"""
import os, zipfile
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension")
os.makedirs("dist", exist_ok=True)
out = os.path.join("dist", "calc-ia-locale.oxt")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in files:
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, root))
print("Créé :", out)
