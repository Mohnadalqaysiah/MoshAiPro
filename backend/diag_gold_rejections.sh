#!/usr/bin/env bash
# (2026-10-14) تشخيص للقراءة فقط: لماذا صدرت إشارة ذهب واحدة فقط منذ افتتاح الاثنين؟
# يقرأ سجلات الـbackend ويعدّ أسباب رفض تحليلات الذهب والفضة لكل فريم.
#   - سطور "GATE: <السبب> [الرمز/الفريم]" تحمل الرمز صراحة.
#   - سطور "REJECTED [..] <السبب>" لا تحمله — تُنسب لآخر "CALIBRATE [الرمز/الفريم]" قبلها
#     (تقريبي إن تداخلت تحليلات متوازية — للإشارة لا للحكم الدقيق).
# التشغيل على السيرفر:  bash backend/diag_gold_rejections.sh [ساعات=72] [الرموز=XAUUSD|XAGUSD]
HOURS="${1:-72}"
SYMS="${2:-XAUUSD|XAGUSD}"

docker logs moshapi_backend --since "${HOURS}h" 2>&1 | awk -v syms="^(${SYMS})/" '
  /CALIBRATE \[/ {
    if (match($0, /CALIBRATE \[[A-Z0-9]+\/[0-9a-z]+\]/)) cur = substr($0, RSTART + 11, RLENGTH - 12)
  }
  /CALIBRATE \[/ && cur ~ syms { analysed[cur]++ }
  /GATE: [A-Z_0-9]+ \[/ {
    if (match($0, /GATE: [A-Z_0-9]+ \[[A-Z0-9]+\/[0-9a-z]+\]/)) {
      s = substr($0, RSTART + 6, RLENGTH - 6); split(s, a, " "); k = a[2]; gsub(/[\[\]]/, "", k)
      if (k ~ syms) gate[k " ← " a[1]]++
    }
    next
  }
  /REJECTED \[/ && cur ~ syms {
    if (match($0, /REJECTED \[[A-Z]+\] [^ ]+/)) rej[cur " ← " substr($0, RSTART + 9, RLENGTH - 9)]++
  }
  /Signal saved: / {
    for (i = 1; i <= NF; i++) if ($i ~ /\//) { s2 = $i; if (s2 ~ syms) saved[s2]++ }
  }
  END {
    print "══ عدد التحليلات (CALIBRATE) لكل رمز/فريم ══"; for (k in analysed) printf "  %6d  %s\n", analysed[k], k
    print "\n══ رفض بفلتر صريح (GATE) ══";            for (k in gate) printf "  %6d  %s\n", gate[k], k
    print "\n══ رفض آخر (REJECTED، منسوب تقريبياً) ══"; for (k in rej) printf "  %6d  %s\n", rej[k], k
    print "\n══ إشارات حُفظت ══";                     for (k in saved) printf "  %6d  %s\n", saved[k], k
  }'
echo
echo "ملاحظة: السجلات قد لا تغطي كل الفترة إن أعيد تشغيل الحاوية (docker logs يبدأ من آخر تشغيل)."
