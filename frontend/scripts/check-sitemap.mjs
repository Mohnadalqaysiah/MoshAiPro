// يتحقق أن public/sitemap.xml متسق مع src/data/blogPosts.js (مصدر الحقيقة للمقالات).
//   node scripts/check-sitemap.mjs              → فحص فقط (exit 1 عند أي خلل)
//   node scripts/check-sitemap.mjs --add-missing → يُلحق كتلة لكل مقال ناقص (ar+en) ثم يعيد الفحص
//
// عمداً لا يعيد توليد الملف كله: lastmod الحالية للمقالات القديمة نتيجة تعديلات
// حقيقية يدوية، وإعادة اشتقاقها من date كانت ستُرجعها لتواريخ أقدم.
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SITEMAP = resolve(ROOT, 'public/sitemap.xml')
const O = 'https://qaffel.com'
const { BLOG_POSTS } = await import(pathToFileURL(resolve(ROOT, 'src/data/blogPosts.js')).href)

let xml = readFileSync(SITEMAP, 'utf8')

const block = (p) => {
  const lm = p.updated || p.date
  const alt = `    <xhtml:link rel="alternate" hreflang="ar" href="${O}/blog/${p.slug}" />
    <xhtml:link rel="alternate" hreflang="en" href="${O}/en/blog/${p.slug}" />
    <xhtml:link rel="alternate" hreflang="x-default" href="${O}/blog/${p.slug}" />`
  return `  <!-- مقالة: ${p.titleAr} (عربي + English) -->
  <url>
    <loc>${O}/blog/${p.slug}</loc>
${alt}
    <lastmod>${lm}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>${O}/en/blog/${p.slug}</loc>
${alt}
    <lastmod>${lm}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
`
}

const entries = () => {
  const m = new Map()
  for (const [, body] of xml.matchAll(/<url>([\s\S]*?)<\/url>/g)) {
    const loc = body.match(/<loc>([^<]+)<\/loc>/)?.[1]
    m.set(loc, { lastmod: body.match(/<lastmod>([^<]+)<\/lastmod>/)?.[1], body })
  }
  return m
}

if (process.argv.includes('--add-missing')) {
  const have = entries()
  const add = BLOG_POSTS.filter((p) => !have.has(`${O}/blog/${p.slug}`))
  if (add.length) {
    xml = xml.replace(/\n<\/urlset>/, `\n${add.map(block).join('\n')}\n</urlset>`)
    writeFileSync(SITEMAP, xml)
    console.log(`أُضيف: ${add.map((p) => p.slug).join(', ')}`)
  }
}

const have = entries()
const errors = []
const slugs = new Set(BLOG_POSTS.map((p) => p.slug))

for (const p of BLOG_POSTS) {
  const want = p.updated || p.date
  for (const loc of [`${O}/blog/${p.slug}`, `${O}/en/blog/${p.slug}`]) {
    const e = have.get(loc)
    if (!e) { errors.push(`ناقص بالـsitemap: ${loc}`); continue }
    if (e.lastmod < want) errors.push(`lastmod قديم: ${loc} (${e.lastmod} < ${want})`)
    for (const hl of ['ar', 'en', 'x-default']) {
      if (!e.body.includes(`hreflang="${hl}"`)) errors.push(`hreflang ${hl} ناقص: ${loc}`)
    }
  }
}
// أي رابط مقال بالـsitemap بلا مقال حقيقي = 404/soft-404 تُرسَل لجوجل
for (const loc of have.keys()) {
  const m = loc.match(/^https:\/\/qaffel\.com(?:\/en)?\/blog\/(.+)$/)
  if (m && !slugs.has(m[1])) errors.push(`رابط بلا مقال: ${loc}`)
}
// تكرار
const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
for (const l of new Set(locs.filter((x, i) => locs.indexOf(x) !== i))) errors.push(`مكرر: ${l}`)

if (errors.length) {
  console.error(`check-sitemap: ${errors.length} خلل\n` + errors.map((e) => ` - ${e}`).join('\n'))
  process.exit(1)
}
console.log(`check-sitemap: OK — ${BLOG_POSTS.length} مقالاً، ${have.size} رابطاً`)
