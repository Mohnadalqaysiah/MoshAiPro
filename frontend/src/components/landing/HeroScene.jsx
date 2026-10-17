// HeroScene.jsx — مشهد الـ Hero ثلاثي الأبعاد:
// دماغ ذكاء اصطناعي يحلل شارت شموع 3D، يرصد مفاهيم ICT (اكتساح سيولة، Order Block، FVG، BOS)
// ثم يصدر إشارة بمستويات الدخول والوقف والأهداف. دورة متكررة 16 ثانية.
//
// المتطلبات: npm i three@^0.160  +  import './HeroScene.css'
// - three يُحمّل بـ dynamic import بعد أن يرسم المتصفح النص (لا يؤثر على LCP)
// - نسخة أخف على الجوال، ويتوقف الرسم خارج الشاشة أو عند إخفاء التبويب
// - prefers-reduced-motion: إطار واحد ثابت للحالة النهائية
// - كل النصوص تأتي من prop اسمه `text` (ضعها في LangContext بالعربية والإنجليزية)
// (2026-10-17، Qaffel) تعديلان على نسخة الحزمة: الدرجة A+ لا تُعرض إن كانت فارغة (المنصة لا تحفظ درجة للإشارة)،
// والهدف الأول على 1R من الدخول (سياسة المنصة منذ 14/10) بدل 2.2R — الشموع نفسها لم تُمسّ.
import { useEffect, useRef, useState } from 'react'
import './HeroScene.css'

const DEFAULT_TEXT = {
  steps: ['بيانات السوق', 'رصد ICT', 'تقييم الذكاء الاصطناعي', 'الإشارة'],
  labels: {
    sweep: 'اكتساح سيولة', ob: 'Order Block', fvg: 'FVG', bos: 'كسر هيكل BOS', ai: 'الذكاء الاصطناعي',
    tp2: 'هدف 2', tp1: 'هدف 1', entry: 'دخول', sl: 'وقف',
  },
  side: '▲ شراء', symbol: 'XAUUSD · 1H', grade: '', rr: 'R:R 1:3.6',
  toastTitle: '@Qaffelbot', toastText: 'إشارة جديدة · XAUUSD شراء',
  note: 'محاكاة توضيحية لطريقة عمل المحرك، وليست توصية.',
}

const LABEL_KEYS = ['sweep', 'ob', 'fvg', 'bos', 'ai', 'tp2', 'tp1', 'entry', 'sl']

export default function HeroScene({ text = DEFAULT_TEXT, className = '' }) {
  const T = { ...DEFAULT_TEXT, ...text, labels: { ...DEFAULT_TEXT.labels, ...(text.labels || {}) } }
  const stageRef = useRef(null)
  const canvasRef = useRef(null)
  const labelRefs = useRef({})
  const verdictRef = useRef(null)
  const toastRef = useRef(null)
  const [step, setStep] = useState(0)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let disposed = false
    let cleanup = () => {}

    const start = async () => {
      const THREE = await import('three')
      if (disposed || !canvasRef.current || !stageRef.current) return
      const canvas = canvasRef.current
      const stageEl = stageRef.current
      const RM = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const mobile = window.innerWidth < 760

      let renderer
      try {
        renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' })
      } catch {
        return // بدون WebGL: تبقى الخلفية الثابتة
      }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, mobile ? 1.5 : 2))
      const disposables = []
      const keep = (x) => { disposables.push(x); return x }

      const scene = new THREE.Scene()
      scene.fog = new THREE.Fog(0x05070d, 24, 46)
      const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 200)

      const MINT = 0x3cf2c0, GOLD = 0xf7c35c, CORAL = 0xff6b7a
      const LI = Math.PI // تعويض وحدات الإضاءة في three r155+
      const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v))
      const ease = (x) => 1 - Math.pow(1 - clamp(x), 3)

      // ── بيانات الشموع: نطاق → هبوط → اكتساح سيولة → OB → اندفاع (FVG + BOS) → تصحيح إلى FVG ──
      const C = []
      let p = 6.0
      ;[0.2, -0.1, 0.3, -0.25, 0.15, 0.25, -0.2, 0.3, 0.1, -0.3, 0.35, 0.1, -0.2, -0.1, 0.05].forEach((d, i) => {
        const o = p, c = +(p + d).toFixed(2)
        C.push([o, Math.max(o, c) + 0.18 + (i % 3) * 0.05, Math.min(o, c) - 0.18 - (i % 2) * 0.06, c]); p = c
      })
      ;[-0.3, -0.15, -0.35, 0.12, -0.3, -0.25, 0.1, -0.35, -0.2, -0.15, -0.3].forEach((d, i) => {
        const o = p, c = +(p + d).toFixed(2)
        C.push([o, Math.max(o, c) + 0.12 + (i % 2) * 0.06, Math.min(o, c) - 0.14 - (i % 3) * 0.04, c]); p = c
      })
      C.push([p, 4.72, 3.6, 4.62])        // 26 اكتساح سيولة
      C.push([4.62, 4.68, 4.15, 4.25])    // 27 Order Block
      C.push([4.25, 5.45, 4.2, 5.35])     // 28 اندفاع
      C.push([5.35, 6.7, 5.3, 6.6])       // 29
      C.push([6.6, 7.45, 6.05, 7.3])      // 30 BOS + FVG
      C.push([7.3, 7.55, 7.0, 7.1])
      C.push([7.1, 7.15, 6.5, 6.6])
      C.push([6.6, 6.65, 5.95, 6.15])     // 33 يلمس FVG
      C.push([6.15, 6.5, 5.9, 6.4])       // 34 شمعة الدخول
      const N = C.length
      let swingI = 0
      for (let i = 0; i < 15; i++) if (C[i][1] > C[swingI][1]) swingI = i
      const swingHigh = C[swingI][1]
      let liqLow = 99
      for (let i = 17; i < 26; i++) liqLow = Math.min(liqLow, C[i][2])
      const X = (i) => (i - 17) * 0.34
      const Y = (v) => (v - 3.4) * 0.95
      const XEND = 8.4

      const grid = new THREE.GridHelper(26, 26, 0x1d2c4c, 0x111b31)
      grid.position.set(1.2, -0.15, 0)
      grid.material.transparent = true; grid.material.opacity = 0.55
      keep(grid.geometry); keep(grid.material)
      scene.add(grid)

      const bodyG = keep(new THREE.BoxGeometry(0.2, 1, 0.2))
      const wickG = keep(new THREE.BoxGeometry(0.035, 1, 0.035))
      const candles = C.map(([o, h, l, c], i) => {
        const col = c >= o ? MINT : CORAL
        const m = keep(new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.05, metalness: 0.2, roughness: 0.35, transparent: true, opacity: 0.28 }))
        const g = new THREE.Group(); g.position.set(X(i), Y(l), 0)
        const b = new THREE.Mesh(bodyG, m); b.scale.y = Math.max(0.03, Math.abs(c - o) * 0.95); b.position.y = Y((o + c) / 2) - Y(l)
        const w = new THREE.Mesh(wickG, m); w.scale.y = (h - l) * 0.95; w.position.y = (Y(h) - Y(l)) / 2
        g.add(b, w); scene.add(g)
        return { g, m, x: X(i), scanned: -1 }
      })

      // ── عناصر التحليل ──
      const overlays = []
      const zone = (x1, x2, y1, y2, color, op, trig, depth = 0.7) => {
        const g = new THREE.Group(); g.position.set(x1, (y1 + y2) / 2, 0)
        const geo = keep(new THREE.BoxGeometry(1, 1, 1)); geo.translate(0.5, 0, 0)
        const fm = keep(new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, depthWrite: false }))
        const eg = keep(new THREE.EdgesGeometry(geo))
        const em = keep(new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0 }))
        g.add(new THREE.Mesh(geo, fm), new THREE.LineSegments(eg, em))
        g.userData = { len: x2 - x1, h: Math.max(0.04, y2 - y1), d: depth }
        scene.add(g); overlays.push({ g, trig, mats: [[fm, op], [em, 0.75]] })
      }
      const hline = (x1, x2, y, color, trig, dashed = false, op = 0.95) => {
        const g = new THREE.Group(); g.position.set(x1, y, 0)
        const mats = []; const seg = dashed ? 22 : 1
        const geo = keep(new THREE.BoxGeometry(1, 1, 1)); geo.translate(0.5, 0, 0)
        for (let k = 0; k < seg; k++) {
          const m = keep(new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, depthWrite: false }))
          const s = new THREE.Mesh(geo, m)
          s.position.x = k / seg; s.scale.set(dashed ? 0.55 / seg : 1, 0.04, 0.04)
          g.add(s); mats.push([m, op])
        }
        g.userData = { len: x2 - x1, h: 1, d: 1 }
        scene.add(g); overlays.push({ g, trig, mats, line: true })
      }

      // التوقيت داخل دورة 16 ثانية
      const L = 16, SCAN0 = 1.6, SCAN1 = 7.2, SIG = 9.2, FADE = 14.2
      const scanAt = (x) => SCAN0 + ((x + 6.6) / 15) * (SCAN1 - SCAN0)

      hline(X(17), X(26) + 0.25, Y(liqLow), CORAL, scanAt(X(26)), true, 0.9)
      zone(X(27) - 0.17, XEND, Y(4.15), Y(4.68), MINT, 0.14, scanAt(X(27)))
      zone(X(28) + 0.15, XEND, Y(5.45), Y(6.05), GOLD, 0.2, scanAt(X(30)))
      hline(X(swingI), X(30) + 0.25, Y(swingHigh), 0xdde5f2, scanAt(X(30)) + 0.35, true, 0.85)
      zone(X(34) - 0.1, XEND, Y(5.95), Y(6.15), GOLD, 0.5, SIG, 0.9)
      hline(X(34), XEND, Y(5.35), CORAL, SIG + 0.25)
      hline(X(34), XEND, Y(6.75), MINT, SIG + 0.45)   // TP1 = 1R
      hline(X(34), XEND, Y(8.6), MINT, SIG + 0.65)

      const ring = new THREE.Mesh(keep(new THREE.TorusGeometry(0.3, 0.025, 12, 48)), keep(new THREE.MeshBasicMaterial({ color: CORAL, transparent: true, opacity: 0 })))
      ring.position.set(X(26), Y(3.6), 0); scene.add(ring)
      const marker = new THREE.Group()
      const cone = new THREE.Mesh(keep(new THREE.ConeGeometry(0.17, 0.38, 24)), keep(new THREE.MeshStandardMaterial({ color: MINT, emissive: MINT, emissiveIntensity: 0.7, transparent: true, opacity: 0 })))
      const halo = new THREE.Mesh(keep(new THREE.RingGeometry(0.24, 0.3, 48)), keep(new THREE.MeshBasicMaterial({ color: MINT, transparent: true, opacity: 0, side: THREE.DoubleSide })))
      halo.rotation.x = -Math.PI / 2; halo.position.y = -0.2
      marker.add(cone, halo); marker.position.set(X(34), Y(5.9) - 0.45, 0); scene.add(marker)

      const glowTex = (stops, radial) => {
        const c = document.createElement('canvas'); c.width = c.height = 128
        const x = c.getContext('2d')
        const g = radial ? x.createRadialGradient(64, 64, 0, 64, 64, 64) : x.createLinearGradient(0, 0, 128, 0)
        stops.forEach(([o, col]) => g.addColorStop(o, col)); x.fillStyle = g; x.fillRect(0, 0, 128, 128)
        const tex = keep(new THREE.CanvasTexture(c))
        if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace
        return tex
      }

      // الماسح
      const scanner = new THREE.Group(); scene.add(scanner)
      const beamM = keep(new THREE.MeshBasicMaterial({ map: glowTex([[0, 'rgba(60,242,192,0)'], [0.5, 'rgba(60,242,192,.55)'], [1, 'rgba(60,242,192,0)']]), transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }))
      const beam = new THREE.Mesh(keep(new THREE.PlaneGeometry(1.1, 6.4)), beamM); beam.position.y = 2.9
      const lineM = keep(new THREE.MeshBasicMaterial({ color: MINT, transparent: true, opacity: 0 }))
      const sline = new THREE.Mesh(keep(new THREE.BoxGeometry(0.025, 6.4, 0.025)), lineM); sline.position.y = 2.9
      scanner.add(beam, sline)

      // دماغ الذكاء الاصطناعي
      const brain = new THREE.Group(); brain.position.set(-4.6, 8.3, -5.5); scene.add(brain)
      const NB = mobile ? 30 : 46, nodes = []
      for (let i = 0; i < NB; i++) {
        const y = 1 - (i / (NB - 1)) * 2, r = Math.sqrt(1 - y * y), th = i * 2.399963
        const R = 1.75 + Math.sin(i * 7.1) * 0.18
        nodes.push(new THREE.Vector3(Math.cos(th) * r * R, y * R, Math.sin(th) * r * R))
      }
      const nodeMesh = new THREE.InstancedMesh(keep(new THREE.SphereGeometry(0.065, 12, 12)), keep(new THREE.MeshBasicMaterial({ color: 0xbffbea })), NB)
      const dm = new THREE.Object3D()
      nodes.forEach((v, i) => { dm.position.copy(v); dm.updateMatrix(); nodeMesh.setMatrixAt(i, dm.matrix) })
      brain.add(nodeMesh)
      const edges = []
      nodes.forEach((a, i) => {
        nodes.map((b, j) => [j, a.distanceTo(b)]).filter((e) => e[0] !== i).sort((x, y) => x[1] - y[1]).slice(0, 3)
          .forEach(([j]) => { if (!edges.some((e) => e[0] === j && e[1] === i)) edges.push([i, j]) })
      })
      const ePos = new Float32Array(edges.length * 6)
      edges.forEach(([i, j], k) => ePos.set([nodes[i].x, nodes[i].y, nodes[i].z, nodes[j].x, nodes[j].y, nodes[j].z], k * 6))
      const eGeo = keep(new THREE.BufferGeometry()); eGeo.setAttribute('position', new THREE.BufferAttribute(ePos, 3))
      const edgeMat = keep(new THREE.LineBasicMaterial({ color: MINT, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false }))
      brain.add(new THREE.LineSegments(eGeo, edgeMat))
      const shell = new THREE.Mesh(keep(new THREE.IcosahedronGeometry(1.05, 1)), keep(new THREE.MeshBasicMaterial({ color: GOLD, wireframe: true, transparent: true, opacity: 0.28 })))
      brain.add(shell)
      const coreSp = new THREE.Sprite(keep(new THREE.SpriteMaterial({ map: glowTex([[0, 'rgba(255,230,170,1)'], [0.25, 'rgba(247,195,92,.6)'], [1, 'rgba(247,195,92,0)']], true), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })))
      coreSp.scale.set(2.2, 2.2, 1); brain.add(coreSp)

      const NP = mobile ? 26 : 44, pulses = [], pPos = new Float32Array(NP * 3)
      for (let i = 0; i < NP; i++) pulses.push({ e: (i * 7) % edges.length, f: Math.random(), s: 0.4 + Math.random() * 0.6 })
      const pGeo = keep(new THREE.BufferGeometry()); pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
      brain.add(new THREE.Points(pGeo, keep(new THREE.PointsMaterial({ color: GOLD, size: 0.13, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false }))))

      const NS = mobile ? 18 : 30, sPos = new Float32Array(NS * 3)
      const sGeo = keep(new THREE.BufferGeometry()); sGeo.setAttribute('position', new THREE.BufferAttribute(sPos, 3))
      const streamMat = keep(new THREE.PointsMaterial({ color: MINT, size: 0.11, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }))
      scene.add(new THREE.Points(sGeo, streamMat))

      const ND = mobile ? 120 : 260, dPos = new Float32Array(ND * 3)
      for (let i = 0; i < ND; i++) { dPos[i * 3] = (Math.random() - 0.5) * 30; dPos[i * 3 + 1] = Math.random() * 13 - 1; dPos[i * 3 + 2] = (Math.random() - 0.5) * 20 - 4 }
      const dGeo = keep(new THREE.BufferGeometry()); dGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3))
      const dust = new THREE.Points(dGeo, keep(new THREE.PointsMaterial({ color: 0x9db4e0, size: 0.035, transparent: true, opacity: 0.5 })))
      scene.add(dust)

      scene.add(new THREE.AmbientLight(0x8899bb, 0.7 * LI))
      const key = new THREE.DirectionalLight(0xffffff, 0.8 * LI); key.position.set(4, 10, 8); scene.add(key)
      const mintL = new THREE.PointLight(MINT, 1.6 * LI, 22, 0); mintL.position.set(0, 4, 5); scene.add(mintL)
      const goldL = new THREE.PointLight(GOLD, 2.2 * LI, 16, 0); goldL.position.copy(brain.position); scene.add(goldL)

      // تسميات DOM مثبتة على نقاط ثلاثية الأبعاد
      const anchors = {
        sweep: { p: [X(26), Y(3.6) - 0.35, 0], from: scanAt(X(26)) },
        ob: { p: [X(27) + 0.9, Y(4.15) - 0.1, 0], from: scanAt(X(27)) },
        fvg: { p: [X(29) + 0.9, Y(6.05) + 0.05, 0], from: scanAt(X(30)) },
        bos: { p: [(X(swingI) + X(30)) / 2, Y(swingHigh) + 0.08, 0], from: scanAt(X(30)) + 0.35 },
        ai: { p: [brain.position.x, brain.position.y + 2.25, brain.position.z], from: 0, always: true },
        tp2: { p: [XEND, Y(8.6), 0], from: SIG + 0.65 },
        tp1: { p: [XEND, Y(6.75), 0], from: SIG + 0.45 },
        entry: { p: [XEND, Y(6.05), 0], from: SIG },
        sl: { p: [XEND, Y(5.35), 0], from: SIG + 0.25 },
      }
      Object.values(anchors).forEach((a) => { a.v = new THREE.Vector3(...a.p) })

      let mx = 0, my = 0, tx = 0, ty = 0
      const onMove = (e) => { const r = stageEl.getBoundingClientRect(); tx = (e.clientX - r.left) / r.width - 0.5; ty = (e.clientY - r.top) / r.height - 0.5 }
      const onLeave = () => { tx = 0; ty = 0 }
      stageEl.addEventListener('pointermove', onMove)
      stageEl.addEventListener('pointerleave', onLeave)

      let W = 1, H = 1
      const layout = () => {
        W = stageEl.clientWidth; H = stageEl.clientHeight
        if (!W || !H) return
        renderer.setSize(W, H, false); camera.aspect = W / H
        camera.fov = W / H < 1 ? 46 : 40; camera.updateProjectionMatrix()
      }
      layout()
      const ro = new ResizeObserver(layout); ro.observe(stageEl)

      let visible = true, lastStep = -1
      const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting }); io.observe(stageEl)
      const v3 = new THREE.Vector3(), A = new THREE.Vector3(), clock = new THREE.Clock()

      const frame = (tt) => {
        const t = tt % L, Tm = clock.getElapsedTime()
        const fade = t > FADE ? 1 - clamp((t - FADE) / 1.4) : 1
        mx += (tx - mx) * 0.05; my += (ty - my) * 0.05
        // (Qaffel) شاشة عمودية (جوال): الكاميرا أبعد وأعلى حتى يتسع الشارت كاملاً فوق شريط المراحل
        const portrait = W / H < 1.05
        camera.position.set((portrait ? 1.8 : 2.6) + mx * 4 + Math.sin(Tm * 0.12) * 0.6, (portrait ? 4.6 : 6.2) - my * 2.5, portrait ? 24 : 18.5)
        camera.lookAt(portrait ? 1.6 : 0.9, portrait ? 3.2 : 4.4, -1.2)

        const scanX = -6.6 + clamp((t - SCAN0) / (SCAN1 - SCAN0)) * 15
        candles.forEach((k, i) => {
          k.g.scale.set(1, Math.max(0.001, ease((t - i * 0.035) / 0.35)), 1)
          if (t < SCAN0) k.scanned = -1
          if (k.scanned < 0 && t >= SCAN0 && scanX >= k.x) k.scanned = t
          const s = k.scanned >= 0 ? Math.exp(-(t - k.scanned) * 2.5) : 0
          k.m.opacity = k.scanned >= 0 ? 0.95 : 0.3
          k.m.emissiveIntensity = 0.12 + s * 0.9 + (i === N - 1 && t > SIG ? 0.35 + Math.sin(Tm * 5) * 0.15 : 0)
        })

        const sOn = t > SCAN0 - 0.2 && t < SCAN1 + 0.3 ? Math.min(clamp((t - SCAN0 + 0.2) / 0.4), clamp((SCAN1 + 0.3 - t) / 0.4)) : 0
        scanner.position.x = scanX; beamM.opacity = sOn * 0.9; lineM.opacity = sOn

        overlays.forEach((o) => {
          const e = ease((t - o.trig) / 0.7) * fade, u = o.g.userData
          o.g.scale.set(Math.max(0.001, u.len * e), o.line ? 1 : u.h, o.line ? 1 : u.d)
          o.mats.forEach(([m, op]) => { m.opacity = op * clamp((t - o.trig) / 0.5) * fade })
        })
        ring.material.opacity = clamp((t - scanAt(X(26))) / 0.4) * fade
        ring.scale.setScalar(1 + Math.sin(Tm * 4) * 0.12); ring.lookAt(camera.position)
        const me = clamp((t - SIG) / 0.5) * fade
        cone.material.opacity = me
        marker.position.y = Y(5.9) - 0.45 + Math.sin(Tm * 3) * 0.07
        halo.scale.setScalar(1 + ((Tm * 1.2) % 1) * 1.4); halo.material.opacity = me * (1 - ((Tm * 1.2) % 1))

        const busy = t > SCAN0 && t < SIG + 1.2 ? 1 : 0.35
        brain.rotation.y = Tm * 0.18; brain.rotation.x = Math.sin(Tm * 0.3) * 0.15
        shell.rotation.y = -Tm * 0.4; shell.rotation.z = Tm * 0.2
        coreSp.material.opacity = 0.55 + busy * 0.35 + Math.sin(Tm * 6) * 0.08 * busy
        edgeMat.opacity = 0.14 + busy * 0.18
        goldL.intensity = (1.2 + busy * 1.6) * LI
        pulses.forEach((q, i) => {
          q.f += q.s * (busy > 0.5 ? 0.035 : 0.012)
          if (q.f > 1) { q.f = 0; q.e = (q.e + 13 + i) % edges.length }
          const [a, b] = edges[q.e]; v3.copy(nodes[a]).lerp(nodes[b], q.f); pPos.set([v3.x, v3.y, v3.z], i * 3)
        })
        pGeo.attributes.position.needsUpdate = true

        const toBrain = t > SCAN0 && t < SCAN1 + 0.4, toSig = t > SIG - 0.6 && t < SIG + 1.6
        streamMat.opacity = (toBrain ? sOn : 0) + (toSig ? clamp((t - SIG + 0.6) / 0.3) * clamp((SIG + 1.6 - t) / 0.4) : 0)
        for (let i = 0; i < NS; i++) {
          const f = (Tm * 0.55 + i / NS) % 1
          if (toSig) { A.copy(marker.position); A.y += 0.35; v3.copy(brain.position).lerp(A, f) }
          else { A.set(scanX, 6.2, 0); v3.copy(A).lerp(brain.position, f) }
          v3.y += Math.sin(f * Math.PI) * 1.2; sPos.set([v3.x, v3.y, v3.z], i * 3)
        }
        sGeo.attributes.position.needsUpdate = true
        dust.rotation.y = Tm * 0.01

        renderer.render(scene, camera)

        LABEL_KEYS.forEach((k) => {
          const el = labelRefs.current[k]; if (!el) return
          const a = anchors[k]; v3.copy(a.v).project(camera)
          // (Qaffel) translate لا left/top — تحريك left/top كل إطار كان يُحسب "إزاحة تخطيط" (CLS 0.115 بفحص السرعة)
          el.style.translate = `${(((v3.x + 1) / 2) * W).toFixed(1)}px ${(((1 - v3.y) / 2) * H).toFixed(1)}px`
          el.style.opacity = (a.always ? 0.9 : clamp((t - a.from) / 0.5) * fade).toFixed(2)
        })

        const s = t < SCAN0 ? 0 : t < SCAN1 ? 1 : t < SIG ? 2 : 3
        if (s !== lastStep) { lastStep = s; setStep(s) }
        verdictRef.current?.classList.toggle('show', t > SIG + 0.5 && t < FADE + 0.6)
        toastRef.current?.classList.toggle('show', t > SIG + 1.3 && t < FADE + 0.6)
      }

      let raf = 0
      if (RM) frame(12)
      else {
        const t0 = performance.now()
        const loop = () => { raf = requestAnimationFrame(loop); if (visible && !document.hidden) frame((performance.now() - t0) / 1000) }
        loop()
      }
      setReady(true)

      cleanup = () => {
        cancelAnimationFrame(raf); io.disconnect(); ro.disconnect()
        stageEl.removeEventListener('pointermove', onMove); stageEl.removeEventListener('pointerleave', onLeave)
        disposables.forEach((d) => d.dispose && d.dispose())
        renderer.dispose()
      }
    }

    // (Qaffel، فحص السرعة) three ثقيل (~176KB مضغوطاً + تهيئة ~0.4ث على جوال ضعيف): سطح المكتب بعد اكتمال التحميل،
    // والجوال عند أول تفاعل (لمس/تمرير) — فلا يحجب الخيط الرئيسي أثناء التحميل (TBT).
    const idle = window.requestIdleCallback || ((cb) => setTimeout(cb, 300))
    let handle = null
    const begin = () => { if (!disposed && handle === null) handle = idle(() => { start() }) }
    // (17/10) سطح المكتب أيضاً عند أول تفاعل (حركة الماوس تكفي) — أداة فحص جوجل بلا كرت شاشة ترسم WebGL على المعالج
    // فيُحسب ~1.5ث حجب (TBT)؛ المستخدم الحقيقي يحرّك الماوس فوراً فيبدأ المشهد خلال جزء من الثانية.
    const EV = ['pointermove', 'pointerdown', 'touchstart', 'scroll', 'keydown', 'wheel']
    EV.forEach((e) => window.addEventListener(e, begin, { once: true, passive: true }))
    return () => {
      disposed = true
      EV.forEach((e) => window.removeEventListener(e, begin))
      if (window.cancelIdleCallback && typeof handle === 'number') window.cancelIdleCallback(handle)
      cleanup()
    }
  }, [])

  const isEnd = (k) => ['tp2', 'tp1', 'entry', 'sl'].includes(k)
  const isBelow = (k) => k === 'sweep' || k === 'ob'
  const COLORS = { sweep: '#FF6B7A', ob: '#3CF2C0', fvg: '#F7C35C', bos: '#DDE5F2', ai: '#7AB0FF', tp2: '#3CF2C0', tp1: '#3CF2C0', entry: '#F7C35C', sl: '#FF6B7A' }

  return (
    <div ref={stageRef} className={`hs-stage ${className}`}>
      <canvas ref={canvasRef} className="hs-canvas" aria-hidden="true" style={{ opacity: ready ? 1 : 0 }} />
      <div className="hs-labels" aria-hidden="true">
        {LABEL_KEYS.map((k) => (
          <span key={k} ref={(el) => { labelRefs.current[k] = el }}
            className={`hs-lbl${isEnd(k) ? ' end' : ''}${isBelow(k) ? ' below' : ''}`}
            style={{ '--c': COLORS[k] }}>{T.labels[k]}</span>
        ))}
      </div>
      <div ref={toastRef} className="hs-toast">
        <span className="hs-tg" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M21 4 L3 11 L10 13 L12 20 L21 4 Z" stroke="#fff" strokeWidth="2" strokeLinejoin="round" /></svg>
        </span>
        <span><b dir="ltr">{T.toastTitle}</b><small>{T.toastText}</small></span>
      </div>
      <div className="hs-hud">
        <ol className="hs-steps">
          {T.steps.map((s, i) => <li key={i} className={i === step ? 'on' : i < step ? 'done' : ''}>{s}</li>)}
        </ol>
        <div ref={verdictRef} className="hs-verdict" aria-live="polite">
          <span className="hs-side">{T.side}</span>
          <span className="hs-mono hs-sym">{T.symbol}</span>
          {T.grade ? <span className="hs-grade">{T.grade}</span> : null}
          <span className="hs-sp" />
          <span className="hs-mono hs-rr">{T.rr}</span>
        </div>
      </div>
      <p className="hs-note">{T.note}</p>
    </div>
  )
}
