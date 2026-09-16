/**
 * StrategyGuide — شرح باني الاستراتيجيات + فحص حيّ للبناء الحالي
 * ================================================================
 * (2026-09-17) بلاغ حقيقي: مستخدم ضبط العتبة على 50، ورأى السجل يعرض
 * "Score 54" مراراً بلا إطلاق، فاستنتج أن النظام معطل. وهو يعمل كما
 * عُرّف: الإطلاق يشترط **منطق المجموعات مع العتبة** لا العتبة وحدها.
 *
 * فالمشكلة ليست نقص شرح بل **قاعدة مركزية غير مرئية**. ولذلك هذا المكوّن
 * لا يكتفي بالتعليم العام: يفحص البناء الحالي ويقول ما الذي سيمنع إطلاقه
 * **قبل** أن يحفظه المستخدم وينتظر تنبيهاً لن يأتي.
 *
 * أهم فحص فيه: مجموع الأوزان دون العتبة ⇒ الاستراتيجية **لا يمكن** أن
 * تُطلق مهما تحققت شروطها. خطأ قاطع يُكتشف بالحساب لا بالانتظار، وكان
 * المستخدم سيكتشفه بعد أيام من الصمت.
 */
import { useState } from 'react';
import {
  GraduationCap, ChevronDown, ChevronUp, AlertTriangle,
  CheckCircle2, XCircle, Lightbulb,
} from 'lucide-react';

const C = {
  surface: '#0F1116', surfaceHi: '#151822', border: '#1E222D',
  gold: '#C9A667', goldSoft: 'rgba(201,166,103,0.13)',
  teal: '#2FD8C4', tealSoft: 'rgba(47,216,196,0.13)',
  red: '#E5555C', redSoft: 'rgba(229,85,92,0.13)',
  blue: '#6FA0FF', blueSoft: 'rgba(111,160,255,0.13)',
  text: '#EDEEF3', sub: '#8B92A5', muted: '#545B6B',
};

const LS_KEY = 'qaffel_strategy_guide_open';

/**
 * فحوص البناء الحالي — كل فحص نشأ من التباس حقيقي لا من افتراض.
 */
export function diagnoseBuild({ groups, conditions, minScore }) {
  const enabled = conditions.filter((c) => c.enabled);
  const totalWeight = Math.min(100, enabled.reduce((a, c) => a + Number(c.weight || 0), 0));
  const out = [];

  if (!enabled.length) {
    out.push({
      level: 'info',
      title: 'لا شروط بعد',
      body: 'أضف شرطاً واحداً على الأقل من قائمة الشروط لتبدأ.',
    });
    return { items: out, totalWeight };
  }

  // الخطأ القاطع: السقف دون العتبة ⇒ استحالة الإطلاق
  if (totalWeight < minScore) {
    out.push({
      level: 'error',
      title: 'هذه الاستراتيجية لن تُطلق أبداً',
      body: `مجموع أوزان شروطك ${totalWeight}، والعتبة ${minScore}. حتى لو تحققت ` +
            `كل الشروط معاً فالدرجة لن تتجاوز ${totalWeight} — أي أنها ستبقى ` +
            `دون العتبة دائماً. اخفض العتبة إلى ${Math.max(10, totalWeight - 5)} أو أقل، ` +
            `أو أضف شروطاً، أو ارفع أوزان الحالية.`,
    });
  }

  // مجموعات AND كبيرة: ممكنة لكن نادرة الوقوع
  groups.forEach((g) => {
    const members = enabled.filter((c) => c.groupId === g.id);
    if (!members.length) return;
    if (g.logic === 'AND' && members.length >= 4) {
      out.push({
        level: 'warn',
        title: `مجموعة «${g.name}» تشترط ${members.length} شروط معاً`,
        body: 'منطق «الكل» يعني أن تخلّف شرط واحد يمنع الإطلاق. كلما زاد عدد ' +
              'الشروط في مجموعة «الكل» ندر وقوعها. جرّب «واحد على الأقل» أو ' +
              '«٢ على الأقل» إن كنت لا تقصد اشتراطها جميعاً.',
      });
    }
    if (g.logic === 'AT_LEAST' && (g.atLeast || 1) > members.length) {
      out.push({
        level: 'error',
        title: `مجموعة «${g.name}» تطلب ${g.atLeast} من ${members.length}`,
        body: 'العدد المطلوب أكبر من عدد الشروط الموجودة — لن تكتمل أبداً.',
      });
    }
  });

  // شروط بلا مجموعة تُترك خارج منطق الإطلاق
  const orphan = enabled.filter((c) => !groups.some((g) => g.id === c.groupId));
  if (orphan.length) {
    out.push({
      level: 'warn',
      title: `${orphan.length} شرط خارج أي مجموعة`,
      body: 'تُحتسب في الدرجة ولا تدخل منطق المجموعات. ضعها في مجموعة إن كنت تريدها شرطاً ملزماً.',
    });
  }

  if (!out.length) {
    out.push({
      level: 'ok',
      title: 'البناء سليم',
      body: `أقصى درجة ممكنة ${totalWeight} والعتبة ${minScore} — قابلة للتحقق. ` +
            'ستُطلق حين يكتمل منطق المجموعات وتبلغ الدرجة العتبة معاً.',
    });
  }
  return { items: out, totalWeight };
}

const LEVEL = {
  error: { icon: XCircle,       color: C.red,  bg: C.redSoft },
  warn:  { icon: AlertTriangle, color: C.gold, bg: C.goldSoft },
  ok:    { icon: CheckCircle2,  color: C.teal, bg: C.tealSoft },
  info:  { icon: Lightbulb,     color: C.blue, bg: C.blueSoft },
};

export default function StrategyGuide({ groups, conditions, minScore }) {
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(LS_KEY) !== 'closed'; } catch { return true; }
  });
  const toggle = () => {
    const next = !open;
    setOpen(next);
    try { localStorage.setItem(LS_KEY, next ? 'open' : 'closed'); } catch { /* تصفّح خاص */ }
  };

  const { items, totalWeight } = diagnoseBuild({ groups, conditions, minScore });
  const worst = items.some((i) => i.level === 'error') ? 'error'
              : items.some((i) => i.level === 'warn') ? 'warn' : 'ok';

  return (
    <div style={{ background: C.surface, border: `1px solid ${C.border}` }}
         className="rounded-2xl overflow-hidden mb-4">

      <button onClick={toggle}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-right">
        <span className="flex items-center gap-2" style={{ color: C.text }}>
          <GraduationCap size={17} style={{ color: C.gold }} />
          <b style={{ fontSize: 13.5 }}>كيف تعمل الاستراتيجية؟</b>
          {worst !== 'ok' && (
            <span style={{
              background: LEVEL[worst].bg, color: LEVEL[worst].color,
              border: `1px solid ${LEVEL[worst].color}`, fontSize: 10.5,
            }} className="px-2 py-0.5 rounded-full">
              {worst === 'error' ? 'يلزم إصلاح' : 'انتبه'}
            </span>
          )}
        </span>
        {open ? <ChevronUp size={15} style={{ color: C.muted }} />
              : <ChevronDown size={15} style={{ color: C.muted }} />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4">

          {/* القاعدة — البوابتان */}
          <div style={{ background: C.surfaceHi, border: `1px solid ${C.border}` }}
               className="rounded-xl p-3.5">
            <div style={{ color: C.sub, fontSize: 11.5 }} className="mb-2.5">
              التنبيه يُرسَل حين <b style={{ color: C.text }}>يتحقق الشرطان معاً</b> — لا أحدهما:
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div style={{ background: C.tealSoft, border: `1px solid ${C.teal}` }}
                   className="rounded-lg p-2.5">
                <div style={{ color: C.teal, fontSize: 12 }} className="font-bold mb-1">
                  ١ · منطق المجموعات
                </div>
                <div style={{ color: C.sub, fontSize: 11, lineHeight: 1.7 }}>
                  كل مجموعة يجب أن تُحقّق منطقها:
                  <br />• <b style={{ color: C.text }}>الكل</b> — تتحقق شروطها جميعاً
                  <br />• <b style={{ color: C.text }}>واحد على الأقل</b> — يكفي شرط واحد
                  <br />• <b style={{ color: C.text }}>٢ على الأقل</b> — عدد تحدّده أنت
                </div>
              </div>
              <div style={{ background: C.goldSoft, border: `1px solid ${C.gold}` }}
                   className="rounded-lg p-2.5">
                <div style={{ color: C.gold, fontSize: 12 }} className="font-bold mb-1">
                  ٢ · الدرجة ≥ العتبة
                </div>
                <div style={{ color: C.sub, fontSize: 11, lineHeight: 1.7 }}>
                  لكل شرط <b style={{ color: C.text }}>وزن</b>. وتُجمع أوزان الشروط
                  المتحققة لتعطي <b style={{ color: C.text }}>الدرجة</b>. فإن بلغت
                  العتبة تحقّق هذا الشرط.
                </div>
              </div>
            </div>
            <div style={{ color: C.muted, fontSize: 10.5 }} className="mt-2.5 leading-relaxed">
              ولهذا قد ترى في السجل درجة <b style={{ color: C.sub }}>فوق</b> عتبتك بلا إطلاق —
              لأن منطق المجموعات لم يكتمل. السجل يشرح السبب لكل حدث الآن.
            </div>
          </div>

          {/* فحص البناء الحالي */}
          <div>
            <div style={{ color: C.sub, fontSize: 11.5 }} className="mb-2">
              فحص بنائك الحالي — أقصى درجة ممكنة{' '}
              <b style={{ color: totalWeight >= minScore ? C.teal : C.red, fontFamily: "'JetBrains Mono', monospace" }}>
                {totalWeight}
              </b>{' '}
              والعتبة{' '}
              <b style={{ color: C.text, fontFamily: "'JetBrains Mono', monospace" }}>{minScore}</b>
            </div>
            <div className="space-y-2">
              {items.map((it, i) => {
                const L = LEVEL[it.level];
                const Icon = L.icon;
                return (
                  <div key={i} style={{ background: L.bg, border: `1px solid ${L.color}` }}
                       className="rounded-lg p-2.5 flex items-start gap-2">
                    <Icon size={14} style={{ color: L.color, marginTop: 2, flexShrink: 0 }} />
                    <div className="min-w-0">
                      <div style={{ color: L.color, fontSize: 12 }} className="font-bold">{it.title}</div>
                      <div style={{ color: C.sub, fontSize: 11, lineHeight: 1.75 }} className="mt-0.5">
                        {it.body}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* نصائح للمبتدئ */}
          <div style={{ background: C.surfaceHi, border: `1px solid ${C.border}` }}
               className="rounded-xl p-3.5">
            <div style={{ color: C.text, fontSize: 12 }} className="font-bold mb-2">
              إن كنت تبدأ الآن
            </div>
            <ol style={{ color: C.sub, fontSize: 11.5, lineHeight: 1.9 }} className="space-y-1 pr-4 list-decimal">
              <li><b style={{ color: C.text }}>ابدأ بثلاثة شروط لا أكثر</b> في مجموعة واحدة
                  منطقها «واحد على الأقل». ستُطلق كثيراً — وهذا مقصود: تتعلّم كيف تتصرّف قبل أن تشدّد.</li>
              <li><b style={{ color: C.text }}>راقب أسبوعاً قبل أن تشدّد.</b> شدّد بناءً على ما رأيته،
                  لا على ما تتوقّعه.</li>
              <li><b style={{ color: C.text }}>كل شرط تضيفه يقلّل عدد التنبيهات.</b> استراتيجية
                  بعشرة شروط قد لا تُطلق شهراً كاملاً — وذلك ليس خللاً.</li>
              <li><b style={{ color: C.text }}>الأطر الزمنية الأعلى أبطأ وأثبت.</b> شرط على
                  <span style={{ fontFamily: "'JetBrains Mono', monospace" }}> 4H </span>
                  يتغيّر مرات قليلة يومياً، وعلى
                  <span style={{ fontFamily: "'JetBrains Mono', monospace" }}> 15m </span>
                  يتغيّر باستمرار.</li>
              <li><b style={{ color: C.text }}>التنبيه ليس أمر شراء.</b> يقول إن شروطك تحققت
                  — والقرار والمخاطرة قرارك.</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
