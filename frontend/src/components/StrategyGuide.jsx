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
 *
 * (2026-09-21) تعريب كامل يتبع مبدّل لغة الموقع — كل نص هنا عربي/إنجليزي
 * معاً عبر isAr، بما فيها نصوص diagnoseBuild المولَّدة ديناميكياً.
 */
import { useState } from 'react';
import { useLang } from '../contexts/LangContext';
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
 * كل عنصر يحمل title/body بالعربي والإنجليزي معاً (titleEn/bodyEn).
 */
export function diagnoseBuild({ groups, conditions, minScore, isAr = true }) {
  const enabled = conditions.filter((c) => c.enabled);
  const totalWeight = Math.min(100, enabled.reduce((a, c) => a + Number(c.weight || 0), 0));
  const out = [];

  if (!enabled.length) {
    out.push({
      level: 'info',
      title: 'لا شروط بعد',
      titleEn: 'No conditions yet',
      body: 'أضف شرطاً واحداً على الأقل من قائمة الشروط لتبدأ.',
      bodyEn: 'Add at least one condition from the library to get started.',
    });
    return { items: out, totalWeight };
  }

  // الخطأ القاطع: السقف دون العتبة ⇒ استحالة الإطلاق
  if (totalWeight < minScore) {
    out.push({
      level: 'error',
      title: 'هذه الاستراتيجية لن تُطلق أبداً',
      titleEn: 'This strategy will never trigger',
      body: `مجموع أوزان شروطك ${totalWeight}، والعتبة ${minScore}. حتى لو تحققت ` +
            `كل الشروط معاً فالدرجة لن تتجاوز ${totalWeight} — أي أنها ستبقى ` +
            `دون العتبة دائماً. اخفض العتبة إلى ${Math.max(10, totalWeight - 5)} أو أقل، ` +
            `أو أضف شروطاً، أو ارفع أوزان الحالية.`,
      bodyEn: `Your conditions' weights add up to ${totalWeight}, and the threshold is ${minScore}. ` +
              `Even if every condition were met at once, the score would never exceed ${totalWeight} — ` +
              `always below the threshold. Lower the threshold to ${Math.max(10, totalWeight - 5)} or less, ` +
              `add more conditions, or raise the existing weights.`,
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
        titleEn: `Group "${g.name}" requires ${members.length} conditions at once`,
        body: 'منطق «الكل» يعني أن تخلّف شرط واحد يمنع الإطلاق. كلما زاد عدد ' +
              'الشروط في مجموعة «الكل» ندر وقوعها. جرّب «واحد على الأقل» أو ' +
              '«٢ على الأقل» إن كنت لا تقصد اشتراطها جميعاً.',
        bodyEn: '"All" logic means a single missing condition blocks the trigger. The more conditions ' +
                'an "All" group has, the rarer it fires. Try "At least one" or "At least 2" ' +
                'if you don\'t mean to require every one of them.',
      });
    }
    if (g.logic === 'AT_LEAST' && (g.atLeast || 1) > members.length) {
      out.push({
        level: 'error',
        title: `مجموعة «${g.name}» تطلب ${g.atLeast} من ${members.length}`,
        titleEn: `Group "${g.name}" requires ${g.atLeast} of ${members.length}`,
        body: 'العدد المطلوب أكبر من عدد الشروط الموجودة — لن تكتمل أبداً.',
        bodyEn: 'The required count exceeds the number of conditions in the group — it can never be met.',
      });
    }
  });

  // شروط بلا مجموعة تُترك خارج منطق الإطلاق
  const orphan = enabled.filter((c) => !groups.some((g) => g.id === c.groupId));
  if (orphan.length) {
    out.push({
      level: 'warn',
      title: `${orphan.length} شرط خارج أي مجموعة`,
      titleEn: `${orphan.length} condition(s) outside any group`,
      body: 'تُحتسب في الدرجة ولا تدخل منطق المجموعات. ضعها في مجموعة إن كنت تريدها شرطاً ملزماً.',
      bodyEn: 'They count toward the score but not toward group logic. Place them in a group if you need them binding.',
    });
  }

  if (!out.length) {
    out.push({
      level: 'ok',
      title: 'البناء سليم',
      titleEn: 'Build looks good',
      body: `أقصى درجة ممكنة ${totalWeight} والعتبة ${minScore} — قابلة للتحقق. ` +
            'ستُطلق حين يكتمل منطق المجموعات وتبلغ الدرجة العتبة معاً.',
      bodyEn: `Max possible score is ${totalWeight} and the threshold is ${minScore} — achievable. ` +
              'It will trigger once group logic is met and the score reaches the threshold together.',
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
  const { lang } = useLang();
  const isAr = lang === 'ar';
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
         dir={isAr ? 'rtl' : 'ltr'}
         className="rounded-2xl overflow-hidden mb-4">

      <button onClick={toggle}
        className={`w-full flex items-center justify-between gap-3 px-4 py-3 ${isAr ? 'text-right' : 'text-left'}`}>
        <span className="flex items-center gap-2" style={{ color: C.text }}>
          <GraduationCap size={17} style={{ color: C.gold }} />
          <b style={{ fontSize: 13.5 }}>{isAr ? 'كيف تعمل الاستراتيجية؟' : 'How does the strategy work?'}</b>
          {worst !== 'ok' && (
            <span style={{
              background: LEVEL[worst].bg, color: LEVEL[worst].color,
              border: `1px solid ${LEVEL[worst].color}`, fontSize: 10.5,
            }} className="px-2 py-0.5 rounded-full">
              {worst === 'error' ? (isAr ? 'يلزم إصلاح' : 'Needs fixing') : (isAr ? 'انتبه' : 'Heads up')}
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
              {isAr ? (
                <>التنبيه يُرسَل حين <b style={{ color: C.text }}>يتحقق الشرطان معاً</b> — لا أحدهما:</>
              ) : (
                <>An alert is sent only when <b style={{ color: C.text }}>both conditions are met together</b> — not just one:</>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div style={{ background: C.tealSoft, border: `1px solid ${C.teal}` }}
                   className="rounded-lg p-2.5">
                <div style={{ color: C.teal, fontSize: 12 }} className="font-bold mb-1">
                  {isAr ? '١ · منطق المجموعات' : '1 · Group logic'}
                </div>
                <div style={{ color: C.sub, fontSize: 11, lineHeight: 1.7 }}>
                  {isAr ? (
                    <>
                      كل مجموعة يجب أن تُحقّق منطقها:
                      <br />• <b style={{ color: C.text }}>الكل</b> — تتحقق شروطها جميعاً
                      <br />• <b style={{ color: C.text }}>واحد على الأقل</b> — يكفي شرط واحد
                      <br />• <b style={{ color: C.text }}>٢ على الأقل</b> — عدد تحدّده أنت
                    </>
                  ) : (
                    <>
                      Every group must satisfy its own logic:
                      <br />• <b style={{ color: C.text }}>All</b> — every condition in it is met
                      <br />• <b style={{ color: C.text }}>At least one</b> — a single condition is enough
                      <br />• <b style={{ color: C.text }}>At least N</b> — a count you choose
                    </>
                  )}
                </div>
              </div>
              <div style={{ background: C.goldSoft, border: `1px solid ${C.gold}` }}
                   className="rounded-lg p-2.5">
                <div style={{ color: C.gold, fontSize: 12 }} className="font-bold mb-1">
                  {isAr ? '٢ · الدرجة ≥ العتبة' : '2 · Score ≥ threshold'}
                </div>
                <div style={{ color: C.sub, fontSize: 11, lineHeight: 1.7 }}>
                  {isAr ? (
                    <>
                      لكل شرط <b style={{ color: C.text }}>وزن</b>. وتُجمع أوزان الشروط
                      المتحققة لتعطي <b style={{ color: C.text }}>الدرجة</b>. فإن بلغت
                      العتبة تحقّق هذا الشرط.
                    </>
                  ) : (
                    <>
                      Every condition has a <b style={{ color: C.text }}>weight</b>. The weights of the
                      conditions that are met are summed into a <b style={{ color: C.text }}>score</b>.
                      Once it reaches the threshold, this gate is satisfied.
                    </>
                  )}
                </div>
              </div>
            </div>
            <div style={{ color: C.muted, fontSize: 10.5 }} className="mt-2.5 leading-relaxed">
              {isAr ? (
                <>ولهذا قد ترى في السجل درجة <b style={{ color: C.sub }}>فوق</b> عتبتك بلا إطلاق —
                لأن منطق المجموعات لم يكتمل. السجل يشرح السبب لكل حدث الآن.</>
              ) : (
                <>That's why the log can show a score <b style={{ color: C.sub }}>above</b> your threshold with no
                trigger — group logic wasn't met. The log now explains the reason for every event.</>
              )}
            </div>
          </div>

          {/* فحص البناء الحالي */}
          <div>
            <div style={{ color: C.sub, fontSize: 11.5 }} className="mb-2">
              {isAr ? (
                <>
                  فحص بنائك الحالي — أقصى درجة ممكنة{' '}
                  <b style={{ color: totalWeight >= minScore ? C.teal : C.red, fontFamily: "'JetBrains Mono', monospace" }}>
                    {totalWeight}
                  </b>{' '}
                  والعتبة{' '}
                  <b style={{ color: C.text, fontFamily: "'JetBrains Mono', monospace" }}>{minScore}</b>
                </>
              ) : (
                <>
                  Checking your current build — max possible score{' '}
                  <b style={{ color: totalWeight >= minScore ? C.teal : C.red, fontFamily: "'JetBrains Mono', monospace" }}>
                    {totalWeight}
                  </b>{' '}
                  vs threshold{' '}
                  <b style={{ color: C.text, fontFamily: "'JetBrains Mono', monospace" }}>{minScore}</b>
                </>
              )}
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
                      <div style={{ color: L.color, fontSize: 12 }} className="font-bold">{isAr ? it.title : it.titleEn}</div>
                      <div style={{ color: C.sub, fontSize: 11, lineHeight: 1.75 }} className="mt-0.5">
                        {isAr ? it.body : it.bodyEn}
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
              {isAr ? 'إن كنت تبدأ الآن' : "If you're just starting"}
            </div>
            {isAr ? (
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
            ) : (
              <ol style={{ color: C.sub, fontSize: 11.5, lineHeight: 1.9 }} className="space-y-1 pl-4 list-decimal">
                <li><b style={{ color: C.text }}>Start with three conditions, no more,</b> in a single group
                    with "At least one" logic. It will trigger often on purpose — you learn how to act before tightening it.</li>
                <li><b style={{ color: C.text }}>Watch it for a week before tightening.</b> Tighten based on what
                    you actually observed, not on what you expect.</li>
                <li><b style={{ color: C.text }}>Every condition you add reduces the number of alerts.</b> A strategy
                    with ten conditions may not trigger for a whole month — that's not a bug.</li>
                <li><b style={{ color: C.text }}>Higher timeframes are slower and steadier.</b> A condition on
                    <span style={{ fontFamily: "'JetBrains Mono', monospace" }}> 4H </span>
                    changes a few times a day, while one on
                    <span style={{ fontFamily: "'JetBrains Mono', monospace" }}> 15m </span>
                    changes constantly.</li>
                <li><b style={{ color: C.text }}>An alert is not a buy order.</b> It only says your conditions
                    were met — the decision and the risk are yours.</li>
              </ol>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
