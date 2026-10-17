// HeroScene.jsx — خلفية الـ Hero ثلاثية الأبعاد (أرض سوق متموّجة + حلقة Q معدنية)
// - تحميل three.js بشكل كسول (dynamic import) بعد أن تصبح الصفحة جاهزة، حتى لا يتأثر LCP
// - نسخة أخف تلقائياً على الجوال، وتوقف الرسم عند الخروج من الشاشة أو إخفاء التبويب
// - prefers-reduced-motion: يُرسم إطار واحد ثابت فقط
// المتطلب: npm i three
import { useEffect, useRef, useState } from 'react'

export default function HeroScene({ className = '' }) {
  const canvasRef = useRef(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let disposed = false
    let cleanup = () => {}

    const start = async () => {
      const THREE = await import('three')
      if (disposed || !canvasRef.current) return
      const canvas = canvasRef.current
      const RM = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const mobile = window.innerWidth < 760

      let renderer
      try {
        renderer = new THREE.WebGLRenderer({ canvas, antialias: !mobile, alpha: true, powerPreference: 'low-power' })
      } catch {
        return // لا WebGL: تبقى الخلفية الثابتة (poster) ظاهرة
      }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, mobile ? 1.5 : 2))

      const scene = new THREE.Scene()
      scene.fog = new THREE.Fog(0x05070d, 18, 46)
      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)

      // ── أعمدة السوق ──
      const COLS = mobile ? 18 : 34
      const ROWS = mobile ? 12 : 20
      const GAP = 1.05
      const geo = new THREE.BoxGeometry(0.62, 1, 0.62)
      geo.translate(0, 0.5, 0)
      const mat = new THREE.MeshStandardMaterial({ metalness: 0.35, roughness: 0.32 })
      const bars = new THREE.InstancedMesh(geo, mat, COLS * ROWS)
      scene.add(bars)
      const dummy = new THREE.Object3D()
      const c = new THREE.Color()
      const cMint = new THREE.Color(0x3cf2c0)
      const cGold = new THREE.Color(0xf7c35c)
      const cCoral = new THREE.Color(0xff6b7a)
      const cDeep = new THREE.Color(0x15203a)
      for (let i = 0; i < COLS * ROWS; i++) bars.setColorAt(i, cDeep)

      // ── حلقة Q ──
      const ringGroup = new THREE.Group()
      const ringGeo = new THREE.TorusGeometry(2.3, 0.26, 40, 180)
      const ringMat = new THREE.MeshStandardMaterial({ color: 0xdde5f2, metalness: 1, roughness: 0.18 })
      const tailGeo = new THREE.CylinderGeometry(0.24, 0.24, 2.2, 32)
      const tailMat = new THREE.MeshStandardMaterial({ color: 0x3cf2c0, metalness: 0.6, roughness: 0.25, emissive: 0x0b4f3e })
      const coreGeo = new THREE.SphereGeometry(0.55, 48, 48)
      const coreMat = new THREE.MeshStandardMaterial({ color: 0xf7c35c, metalness: 0.9, roughness: 0.22, emissive: 0x3a2600 })
      const ring = new THREE.Mesh(ringGeo, ringMat)
      const tail = new THREE.Mesh(tailGeo, tailMat)
      tail.position.set(1.95, -1.95, 0)
      tail.rotation.z = Math.PI / 4
      const core = new THREE.Mesh(coreGeo, coreMat)
      ringGroup.add(ring, tail, core)
      scene.add(ringGroup)

      // ── جزيئات ──
      const PN = mobile ? 220 : 520
      const pPos = new Float32Array(PN * 3)
      for (let i = 0; i < PN; i++) {
        pPos[i * 3] = (Math.random() - 0.5) * 44
        pPos[i * 3 + 1] = Math.random() * 14 + 1
        pPos[i * 3 + 2] = (Math.random() - 0.5) * 30
      }
      const pGeo = new THREE.BufferGeometry()
      pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
      const pMat = new THREE.PointsMaterial({ color: 0x9df7de, size: 0.06, transparent: true, opacity: 0.7 })
      const parts = new THREE.Points(pGeo, pMat)
      scene.add(parts)

      // ── إضاءة ──
      scene.add(new THREE.AmbientLight(0x8899bb, 0.55))
      const key = new THREE.DirectionalLight(0xffffff, 0.9)
      key.position.set(-6, 12, 8)
      scene.add(key)
      const mintL = new THREE.PointLight(0x3cf2c0, 2.2, 30)
      mintL.position.set(-8, 5, 4)
      scene.add(mintL)
      const goldL = new THREE.PointLight(0xf7c35c, 2.4, 26)
      scene.add(goldL)
      const rim = new THREE.PointLight(0x7ab0ff, 1.4, 30)
      rim.position.set(8, 6, -6)
      scene.add(rim)

      // ── تفاعل الماوس ──
      const isRtl = document.documentElement.dir === 'rtl' || document.body.dir === 'rtl' ||
        canvas.closest('[dir="rtl"]') !== null
      let mx = 0, my = 0, tx = 0, ty = 0
      const onMove = (e) => { tx = e.clientX / window.innerWidth - 0.5; ty = e.clientY / window.innerHeight - 0.5 }
      window.addEventListener('pointermove', onMove, { passive: true })

      const layout = () => {
        const w = canvas.clientWidth, h = canvas.clientHeight
        if (!w || !h) return
        renderer.setSize(w, h, false)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
        const wide = w > 960
        // RTL: النص يمين فالحلقة يسار؛ LTR: العكس
        const side = isRtl ? -1 : 1
        ringGroup.position.set(wide ? 6.2 * side : 0, wide ? 4.6 : 5.2, 1)
        ringGroup.scale.setScalar(wide ? 1 : 0.75)
        goldL.position.set(ringGroup.position.x, ringGroup.position.y, 4)
      }
      layout()
      window.addEventListener('resize', layout)

      let visible = true
      const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting })
      io.observe(canvas)

      const clock = new THREE.Clock()
      const frame = () => {
        const t = clock.getElapsedTime()
        mx += (tx - mx) * 0.04
        my += (ty - my) * 0.04
        camera.position.set(Math.sin(t * 0.06) * 3 + mx * 5, 8.5 - my * 3, 17)
        camera.lookAt(0, 2.2, 0)
        let i = 0
        for (let x = 0; x < COLS; x++) {
          for (let z = 0; z < ROWS; z++) {
            const px = (x - COLS / 2) * GAP
            const pz = (z - ROWS / 2) * GAP
            const wave = Math.sin(px * 0.32 + t * 0.9) * Math.cos(pz * 0.28 - t * 0.6) + Math.sin((px + pz) * 0.15 + t * 0.4) * 0.6
            const d = Math.hypot(px - ringGroup.position.x, pz)
            const h = Math.max(0.08, 1.4 + wave * 1.25 + Math.max(0, 2.2 - d * 0.35))
            dummy.position.set(px, -1.2, pz)
            dummy.scale.set(1, h, 1)
            dummy.updateMatrix()
            bars.setMatrixAt(i, dummy.matrix)
            const k = (wave + 1.6) / 3.2
            if (k > 0.72) c.copy(cMint).lerp(cGold, (k - 0.72) * 2.6)
            else if (k < 0.28) c.copy(cDeep).lerp(cCoral, (0.28 - k) * 2.2)
            else c.copy(cDeep).lerp(cMint, (k - 0.28) * 0.55)
            bars.setColorAt(i, c)
            i++
          }
        }
        bars.instanceMatrix.needsUpdate = true
        bars.instanceColor.needsUpdate = true
        ringGroup.rotation.y = Math.sin(t * 0.5) * 0.5 + mx * 0.6
        ringGroup.rotation.x = Math.cos(t * 0.4) * 0.18 - my * 0.4
        core.scale.setScalar(1 + Math.sin(t * 2) * 0.05)
        parts.rotation.y = t * 0.015
        renderer.render(scene, camera)
      }

      let raf = 0
      if (RM) {
        frame()
      } else {
        const loop = () => {
          raf = requestAnimationFrame(loop)
          if (visible && !document.hidden) frame()
        }
        loop()
      }
      setReady(true)

      cleanup = () => {
        cancelAnimationFrame(raf)
        io.disconnect()
        window.removeEventListener('pointermove', onMove)
        window.removeEventListener('resize', layout)
        ;[geo, ringGeo, tailGeo, coreGeo, pGeo].forEach((g) => g.dispose())
        ;[mat, ringMat, tailMat, coreMat, pMat].forEach((m) => m.dispose())
        renderer.dispose()
      }
    }

    // ابدأ بعد أن يرسم المتصفح النص (لا نؤخر LCP)
    const idle = window.requestIdleCallback || ((cb) => setTimeout(cb, 300))
    const handle = idle(() => { start() })

    return () => {
      disposed = true
      if (window.cancelIdleCallback && typeof handle === 'number') window.cancelIdleCallback(handle)
      cleanup()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={className}
      style={{
        position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: -1,
        opacity: ready ? 1 : 0, transition: 'opacity .8s ease',
      }}
    />
  )
}
