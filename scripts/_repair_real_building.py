#!/usr/bin/env python3
"""Run the real RE-SingDetch-FH building through the full CAD-to-5D pipeline."""
import sys, os, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.cad_to_5d_pipeline import CADTo5DPipeline

DXF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "RE-SingDetch-FH_AS", "geometry", "converted.dxf")

def main():
    t0 = time.time()
    dxf = open(DXF, encoding="utf-8", errors="replace").read()
    print("DXF source:", DXF)
    print("DXF bytes:", len(dxf))
    print("DXF sha256:", hashlib.sha256(dxf.encode("utf-8", "replace")).hexdigest())
    pipe = CADTo5DPipeline()
    report = pipe.run(dxf)
    print("TOTAL WALLTIME:", round(time.time() - t0, 1), "s")
    print("DECISION:", report.get("decision"))

if __name__ == "__main__":
    main()
