"""
(2026-11-09، طلب المالك) من اختار فريم 15m بتفضيلات الإشعارات يصير "كل الفريمات" ما دام 15m موقوفاً (timeframe_pause.py)،
وتُحفظ اختياراته السابقة لإرجاعها حين يُعاد الفريم.

    docker exec -i moshapi_backend python - < backend/migrate_15m_prefs.py                 معاينة فقط
    docker exec -i moshapi_backend python - --apply < backend/migrate_15m_prefs.py         تطبيق + نسخة احتياطية
    docker exec -i moshapi_backend python - --restore < backend/migrate_15m_prefs.py       إرجاع من النسخة الاحتياطية

القاعدة: notify_timeframes فيها 15m ← فارغة (= كل الفريمات، اتفاقية المشروع). notify_timeframe القديم (حقل البوت المفرد) 15m ← 1h.
النسخة الاحتياطية بـsite_settings (tf15m_prefs_backup): لكل مستخدم قيمتاه قبل التطبيق. التطبيق مرة ثانية لا يكتب فوقها.
الإرجاع يعيد فقط من لم يغيّر تفضيلاته بعد التطبيق (لا يُمحى اختيار جديد اختاره المستخدم بنفسه).
"""
import json
import sys

BACKUP_KEY = "tf15m_prefs_backup"


def plan_change(timeframes, timeframe):
    """(قائمة جديدة، فريم مفرد جديد) أو None إن لم يتأثر."""
    tfs = [t for t in (timeframes or []) if t != "all"]
    hit = "15m" in tfs or timeframe == "15m"
    if not hit:
        return None
    return ([] if "15m" in tfs else tfs), ("1h" if timeframe == "15m" else timeframe)


def main():
    from app.database import SessionLocal
    from app.models.site_settings import SiteSettings
    from app.models.user import User

    mode = "--apply" if "--apply" in sys.argv else "--restore" if "--restore" in sys.argv else "preview"
    db = SessionLocal()
    row = db.query(SiteSettings).filter(SiteSettings.key == BACKUP_KEY).first()
    backup = json.loads(row.value) if row and row.value else {}

    if mode == "--restore":
        if not backup:
            print("لا نسخة احتياطية — لا شيء يُرجَع.")
            return
        done = skipped = 0
        for uid, prev in backup.items():
            u = db.query(User).filter(User.id == int(uid)).first()
            if not u:
                continue
            now_tfs = [t for t in (u.notify_timeframes or []) if t != "all"]
            if now_tfs != prev["after_timeframes"] or u.notify_timeframe != prev["after_timeframe"]:
                skipped += 1                                        # غيّر تفضيلاته بنفسه بعد التطبيق
                continue
            u.notify_timeframes, u.notify_timeframe = prev["timeframes"], prev["timeframe"]
            done += 1
        row.value = json.dumps({}, ensure_ascii=False)
        db.commit()
        print(f"أُرجع {done} مستخدماً، وتُرك {skipped} غيّروا تفضيلاتهم بأنفسهم.")
        return

    changes = []
    for u in db.query(User).all():
        c = plan_change(u.notify_timeframes, u.notify_timeframe)
        if c:
            changes.append((u, c))
    print(f"{'تطبيق' if mode == '--apply' else 'معاينة'}: {len(changes)} مستخدماً اختاروا 15m")
    for u, (tfs, tf) in changes[:60]:
        print(f"  #{u.id} @{u.telegram_username or '—'} {sorted(u.notify_timeframes or [])} → {tfs or 'كل الفريمات'}")
    if mode != "--apply":
        print("\nللتطبيق: أضف --apply")
        return
    for u, (tfs, tf) in changes:
        backup.setdefault(str(u.id), {"timeframes": list(u.notify_timeframes or []), "timeframe": u.notify_timeframe,
                                      "after_timeframes": tfs, "after_timeframe": tf})
        u.notify_timeframes, u.notify_timeframe = tfs, tf
    if row is None:
        row = SiteSettings(key=BACKUP_KEY, description="نسخة تفضيلات 15m قبل إيقافه (migrate_15m_prefs.py)")
        db.add(row)
    row.value = json.dumps(backup, ensure_ascii=False)
    db.commit()
    print(f"\nطُبّق على {len(changes)}، والنسخة الاحتياطية فيها {len(backup)} مستخدماً.")


if __name__ == "__main__":
    main()
