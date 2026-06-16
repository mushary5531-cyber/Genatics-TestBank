import React, {
  useState, useEffect, useCallback, useMemo, useRef
} from "react";
import { createRoot } from "react-dom/client";

// ─── Types ───────────────────────────────────────────────────────────────────
export type Question = {
  id: string;
  exam: string;       // "mid1" | "mid2" | "final"
  lecture: string;
  q: string;
  options: string[];
  answer: number;
  explanation: string;
  image?: string;
  source?: string;    // e.g. "Med 25", "Med 24", "Med 18"
};

type QuizAnswer = { questionId: string; chosen: number; correct: boolean; skipped?: boolean };
type Screen = "home" | "quiz" | "result" | "review";

// ─── Questions data (injected by inject.py) ──────────────────────────────────
const ALL_QUESTIONS: Question[] = [];
// INJECT_MARKER

// ─── LocalStorage helpers ────────────────────────────────────────────────────
const LS_SEEN = "gbq_seen";
const LS_HISTORY = "gbq_history";
const getSeen = (): Set<string> =>
  new Set(JSON.parse(localStorage.getItem(LS_SEEN) || "[]"));
const addSeen = (ids: string[]) => {
  const s = getSeen();
  ids.forEach((id) => s.add(id));
  localStorage.setItem(LS_SEEN, JSON.stringify([...s]));
};
const resetSeen = () => localStorage.removeItem(LS_SEEN);

// ─── Confetti ─────────────────────────────────────────────────────────────────
function Confetti() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const pieces: {
      x: number; y: number; w: number; h: number;
      color: string; rot: number; vx: number; vy: number; vr: number;
    }[] = [];
    const colors = ["#818cf8","#38bdf8","#a78bfa","#f472b6","#34d399","#fbbf24"];
    for (let i = 0; i < 140; i++) {
      pieces.push({
        x: Math.random() * canvas.width,
        y: -20 - Math.random() * 200,
        w: 8 + Math.random() * 8,
        h: 4 + Math.random() * 4,
        color: colors[Math.floor(Math.random() * colors.length)],
        rot: Math.random() * Math.PI * 2,
        vx: (Math.random() - 0.5) * 3,
        vy: 2 + Math.random() * 4,
        vr: (Math.random() - 0.5) * 0.2,
      });
    }
    let frame: number;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach((p) => {
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
        p.x += p.vx;
        p.y += p.vy;
        p.rot += p.vr;
      });
      frame = requestAnimationFrame(draw);
    };
    draw();
    const t = setTimeout(() => cancelAnimationFrame(frame), 4000);
    return () => { cancelAnimationFrame(frame); clearTimeout(t); };
  }, []);
  return (
    <canvas
      ref={canvasRef}
      style={{ position:"fixed", inset:0, pointerEvents:"none", zIndex:9999 }}
    />
  );
}

// ─── Aurora background ────────────────────────────────────────────────────────
function Aurora() {
  return (
    <div style={{ position:"fixed", inset:0, overflow:"hidden", zIndex:0, pointerEvents:"none" }}>
      <div className="aurora-blob aurora-1" />
      <div className="aurora-blob aurora-2" />
      <div className="aurora-blob aurora-3" />
    </div>
  );
}

// ─── Progress ring SVG ────────────────────────────────────────────────────────
function Ring({ pct, size = 160 }: { pct: number; size?: number }) {
  const r = (size - 20) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 90 ? "#34d399" : pct >= 60 ? "#818cf8" : "#f87171";
  return (
    <svg width={size} height={size} style={{ transform:"rotate(-90deg)" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none"
        stroke="rgba(255,255,255,0.08)" strokeWidth={10} />
      <circle cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={10}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        style={{ transition:"stroke-dasharray 1s ease" }}
      />
      <text x={size/2} y={size/2}
        textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size * 0.2} fontWeight={700}
        style={{ transform:`rotate(90deg) translate(0,0)`, transformOrigin:`${size/2}px ${size/2}px`, fontFamily:"Cairo,sans-serif" }}>
        {pct}%
      </text>
    </svg>
  );
}

// ─── Lecture bar ──────────────────────────────────────────────────────────────
function LectureBar({ name, correct, total }: { name:string; correct:number; total:number }) {
  const pct = total ? Math.round((correct / total) * 100) : 0;
  const color = pct >= 90 ? "#34d399" : pct >= 60 ? "#818cf8" : "#f87171";
  return (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4, fontSize:13, color:"rgba(255,255,255,0.7)" }}>
        <span>{name}</span>
        <span style={{ color }}>{correct}/{total} ({pct}%)</span>
      </div>
      <div style={{ height:8, background:"rgba(255,255,255,0.08)", borderRadius:99, overflow:"hidden" }}>
        <div style={{
          height:"100%", width:`${pct}%`, borderRadius:99,
          background:`linear-gradient(90deg,${color}99,${color})`,
          boxShadow:`0 0 8px ${color}88`,
          transition:"width 1s ease",
        }} />
      </div>
      {pct < 60 && (
        <div style={{ marginTop:4, fontSize:11, color:"#f87171" }}>
          ⚠️ تحتاج مراجعة — أقل من 60%
        </div>
      )}
    </div>
  );
}

// ─── Chip component ───────────────────────────────────────────────────────────
function Chip({ label, active, onClick }: { label:string; active:boolean; onClick:()=>void }) {
  return (
    <button onClick={onClick} className={`chip ${active ? "chip-active" : ""}`}>
      {label}
    </button>
  );
}

// ─── Option button ────────────────────────────────────────────────────────────
function OptionBtn({
  text, index, chosen, correct, locked, onClick,
}: {
  text:string; index:number; chosen:number|null; correct:number;
  locked:boolean; onClick:(i:number)=>void;
}) {
  let cls = "opt-btn";
  if (locked) {
    if (index === correct) cls += " opt-correct";
    else if (index === chosen) cls += " opt-wrong";
    else cls += " opt-dim";
  }
  if (locked && index === correct) cls += " anim-bounce";
  if (locked && index === chosen && index !== correct) cls += " anim-shake";

  return (
    <button className={cls} onClick={() => !locked && onClick(index)}
      style={{ animationDelay:`${index * 0.07}s` }}>
      <span className="opt-letter">
        {["A","B","C","D"][index]}
      </span>
      <span>{text}</span>
    </button>
  );
}

// ─── Home / setup screen ──────────────────────────────────────────────────────
function HomeScreen({ onStart }: { onStart:(qs:Question[])=>void }) {
  const [examFilter, setExamFilter] = useState<string>("all");
  const [selLectures, setSelLectures] = useState<Set<string>>(new Set());
  const [count, setCount] = useState(20);
  const [hideSeen, setHideSeen] = useState(false);
  const [seen, setSeen] = useState<Set<string>>(getSeen());

  const examTabs = [
    { id:"all", label:"الكل" },
    { id:"mid1", label:"ميد ١" },
    { id:"mid2", label:"ميد ٢" },
    { id:"final", label:"فاينل" },
  ];

  const byExam = useMemo(() =>
    examFilter === "all" ? ALL_QUESTIONS : ALL_QUESTIONS.filter(q => q.exam === examFilter),
    [examFilter]
  );

  const lectures = useMemo(() => [...new Set(byExam.map(q => q.lecture))].sort(), [byExam]);

  useEffect(() => { setSelLectures(new Set(lectures)); }, [lectures]);

  const filtered = useMemo(() => {
    let qs = byExam.filter(q => selLectures.has(q.lecture));
    if (hideSeen) qs = qs.filter(q => !seen.has(q.id));
    return qs;
  }, [byExam, selLectures, hideSeen, seen]);

  const maxCount = filtered.length;
  const safeCount = Math.min(count, maxCount);

  function toggleLecture(lec: string) {
    setSelLectures(prev => {
      const n = new Set(prev);
      if (n.has(lec)) n.delete(lec); else n.add(lec);
      return n;
    });
  }

  function start() {
    const shuffled = [...filtered].sort(() => Math.random() - 0.5);
    onStart(shuffled.slice(0, safeCount));
  }

  return (
    <div className="screen-center fade-in">
      <h1 className="main-title shimmer-text">Genetics TestBank</h1>
      <p className="subtitle">اختبارات تفاعلية — جينيتكس</p>

      {/* Exam tabs */}
      <div className="glass-card stagger-1">
        <h3 className="section-label">الاختبار</h3>
        <div className="tab-row">
          {examTabs.map(t => (
            <button key={t.id}
              className={`tab-btn ${examFilter === t.id ? "tab-active" : ""}`}
              onClick={() => setExamFilter(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Lectures */}
      <div className="glass-card stagger-2">
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
          <h3 className="section-label" style={{ margin:0 }}>المحاضرات</h3>
          <div style={{ display:"flex", gap:8 }}>
            <button className="link-btn" onClick={() => setSelLectures(new Set(lectures))}>
              تحديد الكل
            </button>
            <span style={{ color:"rgba(255,255,255,0.3)" }}>|</span>
            <button className="link-btn" onClick={() => setSelLectures(new Set())}>
              إلغاء الكل
            </button>
          </div>
        </div>
        <div className="chip-wrap">
          {lectures.map(l => (
            <Chip key={l} label={l} active={selLectures.has(l)} onClick={() => toggleLecture(l)} />
          ))}
          {lectures.length === 0 && (
            <span style={{ color:"rgba(255,255,255,0.4)", fontSize:13 }}>لا توجد محاضرات</span>
          )}
        </div>
      </div>

      {/* Count slider */}
      <div className="glass-card stagger-3">
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:12 }}>
          <h3 className="section-label" style={{ margin:0 }}>عدد الأسئلة</h3>
          <span style={{ color:"#818cf8", fontWeight:700, fontSize:18 }}>{safeCount}</span>
        </div>
        <input type="range" min={1} max={Math.max(maxCount,1)} value={safeCount}
          className="custom-slider"
          onChange={e => setCount(+e.target.value)} />
        <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, color:"rgba(255,255,255,0.4)", marginTop:4 }}>
          <span>1</span>
          <span>{maxCount} متاح</span>
        </div>
      </div>

      {/* Hide seen */}
      <div className="glass-card stagger-4" style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <div style={{ fontWeight:600, fontSize:15 }}>إخفاء الأسئلة المشاهدة</div>
          <div style={{ fontSize:12, color:"rgba(255,255,255,0.4)", marginTop:2 }}>
            {seen.size} سؤال تمت مشاهدته
          </div>
        </div>
        <div style={{ display:"flex", gap:12, alignItems:"center" }}>
          {seen.size > 0 && (
            <button className="link-btn" onClick={() => { resetSeen(); setSeen(new Set()); }}>
              إعادة تعيين
            </button>
          )}
          <button className={`toggle-btn ${hideSeen ? "toggle-on" : ""}`}
            onClick={() => setHideSeen(h => !h)}>
            <span className="toggle-knob" />
          </button>
        </div>
      </div>

      <button className="start-btn glow-pulse stagger-5"
        onClick={start} disabled={safeCount === 0}>
        {safeCount === 0 ? "لا توجد أسئلة" : `ابدأ الاختبار — ${safeCount} سؤال`}
      </button>
    </div>
  );
}

// ─── Quiz screen ──────────────────────────────────────────────────────────────
function QuizScreen({
  questions, onFinish,
}: {
  questions: Question[];
  onFinish: (answers: QuizAnswer[]) => void;
}) {
  const [idx, setIdx] = useState(0);
  const [chosen, setChosen] = useState<number | null>(null);
  const [locked, setLocked] = useState(false);
  const [answers, setAnswers] = useState<QuizAnswer[]>([]);
  const [slideKey, setSlideKey] = useState(0);

  const q = questions[idx];
  const progress = ((idx) / questions.length) * 100;

  function pick(i: number) {
    if (locked) return;
    setChosen(i);
    setLocked(true);
    const correct = i === q.answer;
    setAnswers(prev => [...prev, { questionId: q.id, chosen: i, correct }]);
  }

  function goNext() {
    if (idx + 1 < questions.length) {
      setIdx(i => i + 1);
      setChosen(null);
      setLocked(false);
      setSlideKey(k => k + 1);
    } else {
      addSeen(questions.map(q => q.id));
      onFinish(answers);
    }
  }

  function skip() {
    if (locked) return;
    const updated = [...answers, { questionId: q.id, chosen: -1, correct: false, skipped: true }];
    setAnswers(updated);
    if (idx + 1 < questions.length) {
      setIdx(i => i + 1);
      setChosen(null);
      setLocked(false);
      setSlideKey(k => k + 1);
    } else {
      addSeen(questions.map(q => q.id));
      onFinish(updated);
    }
  }

  function goPrev() {
    if (idx === 0) return;
    setIdx(i => i - 1);
    const prev = answers[idx - 1];
    setChosen(prev?.chosen ?? null);
    setLocked(true);
    setSlideKey(k => k + 1);
  }

  return (
    <div className="screen-center fade-in">
      {/* Progress */}
      <div style={{ marginBottom:20, width:"100%", maxWidth:680 }}>
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6, fontSize:13, color:"rgba(255,255,255,0.5)" }}>
          <span>{q.lecture}</span>
          <span>{idx + 1} / {questions.length}</span>
        </div>
        <div style={{ height:6, background:"rgba(255,255,255,0.08)", borderRadius:99, overflow:"hidden" }}>
          <div style={{
            height:"100%", width:`${progress}%`, borderRadius:99,
            background:"linear-gradient(90deg,#4f46e5,#38bdf8)",
            boxShadow:"0 0 10px #818cf888",
            transition:"width 0.4s ease",
          }} />
        </div>
      </div>

      {/* Question card */}
      <div className="glass-card" style={{ width:"100%", maxWidth:680 }}>
        <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:12 }}>
          <div className="exam-badge" style={{ marginBottom:0 }}>{q.exam.toUpperCase()}</div>
          {q.source && <div className="source-badge">{q.source}</div>}
        </div>
        <p className="question-text" dir="auto">{q.q}</p>

        {q.image && (
          <img src={q.image} alt="question" style={{
            maxWidth:"100%", maxHeight:220, width:"auto", display:"block",
            margin:"0 auto 14px", borderRadius:10,
            border:"1px solid rgba(255,255,255,0.1)"
          }} />
        )}

        <div key={slideKey} className="options-wrap">
          {q.options.map((opt, i) => (
            <OptionBtn key={i} text={opt} index={i}
              chosen={chosen} correct={q.answer}
              locked={locked} onClick={pick} />
          ))}
        </div>

        {locked && (
          <div className={`explanation ${chosen === q.answer ? "expl-correct" : "expl-wrong"}`}>
            <span style={{ fontWeight:700, marginLeft:6 }}>
              {chosen === q.answer ? "✓ صحيح!" : "✗ خطأ!"}
            </span>
            {q.explanation}
          </div>
        )}

        <div style={{ display:"flex", justifyContent:"space-between", marginTop:20 }}>
          <button className="nav-btn" onClick={goPrev} disabled={idx === 0}>
            ← السابق
          </button>
          {!locked && (
            <button className="nav-btn" onClick={skip} style={{ color:"rgba(255,255,255,0.5)" }}>
              تخطي ⟶
            </button>
          )}
          {locked && (
            <button className="nav-btn nav-primary" onClick={goNext}>
              {idx + 1 === questions.length ? "النتيجة →" : "التالي →"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Result screen ────────────────────────────────────────────────────────────
function ResultScreen({
  questions, answers, onReview, onHome,
}: {
  questions: Question[];
  answers: QuizAnswer[];
  onReview: () => void;
  onHome: () => void;
}) {
  const total = answers.length;
  const correct = answers.filter(a => a.correct).length;
  const skippedCount = answers.filter(a => a.skipped).length;
  const pct = total ? Math.round((correct / total) * 100) : 0;

  const lectureStats = useMemo(() => {
    const map: Record<string, { correct:number; total:number }> = {};
    questions.forEach((q, i) => {
      const a = answers[i];
      if (!a) return;
      if (!map[q.lecture]) map[q.lecture] = { correct:0, total:0 };
      map[q.lecture].total++;
      if (a.correct) map[q.lecture].correct++;
    });
    return map;
  }, [questions, answers]);

  const wrongCount = answers.filter(a => !a.correct && !a.skipped).length;
  const reviewCount = wrongCount + skippedCount;

  return (
    <div className="screen-center fade-in">
      {pct >= 90 && <Confetti />}
      <h2 className="main-title shimmer-text" style={{ fontSize:28 }}>النتيجة</h2>

      <div className="glass-card" style={{ textAlign:"center", maxWidth:440 }}>
        <div style={{ display:"flex", justifyContent:"center", marginBottom:16 }}>
          <Ring pct={pct} />
        </div>
        <div style={{ fontSize:20, fontWeight:700, color:"rgba(255,255,255,0.9)" }}>
          {correct} من {total} إجابة صحيحة
        </div>
        {skippedCount > 0 && (
          <div style={{ marginTop:6, fontSize:14, color:"rgba(255,255,255,0.45)" }}>
            ({skippedCount} سؤال متخطي)
          </div>
        )}
        {pct >= 90 && (
          <div style={{ marginTop:8, color:"#34d399", fontWeight:600 }}>
            🎉 ممتاز! نتيجة رائعة
          </div>
        )}
      </div>

      <div className="glass-card" style={{ maxWidth:520, width:"100%" }}>
        <h3 className="section-label">تفصيل المحاضرات</h3>
        {Object.entries(lectureStats).map(([name, stat]) => (
          <LectureBar key={name} name={name} correct={stat.correct} total={stat.total} />
        ))}
      </div>

      <div style={{ display:"flex", gap:12, flexWrap:"wrap", justifyContent:"center" }}>
        {reviewCount > 0 && (
          <button className="nav-btn nav-primary" onClick={onReview}>
            مراجعة الأخطاء والمتخطيات ({reviewCount})
          </button>
        )}
        <button className="nav-btn" onClick={onHome}>
          الرئيسية
        </button>
      </div>
    </div>
  );
}

// ─── Review screen ────────────────────────────────────────────────────────────
function ReviewScreen({
  questions, answers, onHome,
}: {
  questions: Question[];
  answers: QuizAnswer[];
  onHome: () => void;
}) {
  const toReview = useMemo(() =>
    questions.map((q, i) => ({ q, a: answers[i] }))
      .filter(({ a }) => a && !a.correct),
    [questions, answers]
  );

  return (
    <div className="screen-center fade-in">
      <h2 className="main-title shimmer-text" style={{ fontSize:28 }}>
        مراجعة — {toReview.length} سؤال
      </h2>

      {toReview.map(({ q, a }, idx) => (
        <div key={q.id} className="glass-card review-card" style={{ maxWidth:680, width:"100%" }}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:10, flexWrap:"wrap", gap:6 }}>
            <div style={{ display:"flex", gap:6 }}>
              <span className="exam-badge" style={{ marginBottom:0 }}>{q.exam.toUpperCase()}</span>
              {q.source && <span className="source-badge">{q.source}</span>}
            </div>
            <span style={{ fontSize:12, color:"rgba(255,255,255,0.4)" }}>{q.lecture}</span>
          </div>
          {a?.skipped && (
            <div style={{ marginBottom:8, fontSize:13, color:"rgba(251,191,36,0.8)", fontWeight:600 }}>
              ⟶ تم تخطي هذا السؤال
            </div>
          )}
          <p className="question-text" dir="auto" style={{ marginBottom:12 }}>{q.q}</p>

          {q.image && (
            <img src={q.image} alt="question" style={{
              maxWidth:"100%", maxHeight:220, width:"auto", display:"block",
              margin:"0 auto 12px", borderRadius:10,
              border:"1px solid rgba(255,255,255,0.1)"
            }} />
          )}

          {q.options.map((opt, i) => {
            let cls = "opt-btn opt-dim";
            if (i === q.answer) cls = "opt-btn opt-correct";
            else if (!a?.skipped && i === a?.chosen) cls = "opt-btn opt-wrong";
            return (
              <button key={i} className={cls} style={{ cursor:"default" }}>
                <span className="opt-letter">{["A","B","C","D"][i]}</span>
                <span>{opt}</span>
              </button>
            );
          })}

          <div className={`explanation ${a?.skipped ? "expl-wrong" : "expl-wrong"}`} style={{ marginTop:12 }}>
            <span style={{ fontWeight:700, marginLeft:6 }}>الشرح:</span>
            {q.explanation}
          </div>
        </div>
      ))}

      <button className="nav-btn" onClick={onHome} style={{ marginTop:8 }}>
        الرئيسية
      </button>
    </div>
  );
}

// ─── App root ─────────────────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [activeQs, setActiveQs] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<QuizAnswer[]>([]);

  function startQuiz(qs: Question[]) {
    setActiveQs(qs);
    setScreen("quiz");
  }

  function finishQuiz(ans: QuizAnswer[]) {
    setAnswers(ans);
    setScreen("result");
  }

  return (
    <>
      <Aurora />
      <div style={{ position:"relative", zIndex:1, minHeight:"100vh", padding:"24px 16px" }}>
        {screen === "home" && <HomeScreen onStart={startQuiz} />}
        {screen === "quiz" && (
          <QuizScreen questions={activeQs} onFinish={finishQuiz} />
        )}
        {screen === "result" && (
          <ResultScreen
            questions={activeQs} answers={answers}
            onReview={() => setScreen("review")}
            onHome={() => setScreen("home")}
          />
        )}
        {screen === "review" && (
          <ReviewScreen
            questions={activeQs} answers={answers}
            onHome={() => setScreen("home")}
          />
        )}
      </div>
    </>
  );
}
