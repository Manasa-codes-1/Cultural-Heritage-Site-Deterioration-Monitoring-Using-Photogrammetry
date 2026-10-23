import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))

from app.core.database import SessionLocal
from app.models.heritage import Site, Survey, Reconstruction, TemporalComparison, DeteriorationDetection, Deterioration3DMapping

db = SessionLocal()
sites = db.query(Site).all()
print(f"Total Sites: {len(sites)}")
for s in sites:
    surveys = db.query(Survey).filter(Survey.site_id == s.id).all()
    print(f"\nSite: '{s.name}' (id={s.id})")
    print(f"  Surveys ({len(surveys)}):")
    for sv in surveys:
        recs = db.query(Reconstruction).filter(Reconstruction.survey_id == sv.id).all()
        dets = db.query(DeteriorationDetection).filter(DeteriorationDetection.survey_id == sv.id).all()
        maps = db.query(Deterioration3DMapping).filter(Deterioration3DMapping.survey_id == sv.id).all()
        rec_info = ", ".join([f"rec_demo={r.is_demo}" for r in recs]) if recs else "no reconstruction"
        print(f"    - Survey: '{sv.survey_code}' (date={sv.survey_date}, imgs={len(sv.images)}, dets={len(dets)}, maps={len(maps)}, {rec_info})")

comps = db.query(TemporalComparison).all()
print(f"\nTotal Temporal Comparisons: {len(comps)}")
for c in comps:
    print(f"  - Comparison {c.id}: is_demo={c.is_demo}, align_status={c.alignment_status}, change_method={c.change_detection_method}")
