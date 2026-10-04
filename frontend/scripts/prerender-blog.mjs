// يُشغَّل بعد `vite build`: يكتب HTML ثابت لمقالات محدّدة (تجربة) بحيث يحمل الـHTML
// الخام نفس title/description/canonical/hreflang/OG/Article-schema اللي يضبطها
// useSEO بعد الرندر — بدل canonical الرئيسية الموروث من index.html.
//
// المخرجات: dist/blog/<slug>.html و dist/en/blog/<slug>.html (يخدمها nginx عبر
// try_files $uri $uri.html). لا يلمس أي URL ولا الـsitemap.
//
// فشل أي استبدال = فشل البناء (لا نشر بصمت بنسخة ناقصة).
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DIST = resolve(ROOT, 'dist')
const ORIGIN = 'https://qaffel.com'

// مرحلة التجربة (2026-10-04): 3 مقالات فقط. التعميم بعد مراقبة 14 يوماً.
const TRIAL_SLUGS = [
  'best-trading-strategy-guide',
  'best-time-to-trade-gold',
  'best-market-analysis-method',
  // الذراع الثاني (2026-10-05): صفحات "زُحف ولم تُفهرس" بـGSC — لا شيء مفهرس لنخسره
  'ai-trading-middle-east-gulf-guide',
  'ai-gold-trading-bot-saudi-arabia',
  'ict-strategy-automation',
]

const { BLOG_POSTS } = await import(pathToFileURL(resolve(ROOT, 'src/data/blogPosts.js')).href)
const template = readFileSync(resolve(DIST, 'index.html'), 'utf8')

const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

// يستبدل نمطاً واحداً بالضبط — يرمي خطأ لو ما وُجد (القالب تغيّر)
function sub(html, re, replacement, label) {
  if (!re.test(html)) throw new Error(`prerender: لم يُعثر على "${label}" في dist/index.html`)
  return html.replace(re, () => replacement)
}

// نفس معالجة renderInline بـBlogPost.jsx: [نص](رابط) → <a>
// prefix = '' | '/en' — روابط داخلية بلغة الصفحة، مثل renderInline بالكلاينت
function inline(text, prefix) {
  return esc(text).replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
    const external = !url.startsWith('/')
    return `<a href="${external ? url : prefix + url}"${external ? ' rel="noopener noreferrer" target="_blank"' : ''}>${label}</a>`
  })
}

function renderBody(items, prefix) {
  const out = []
  for (let i = 0; i < items.length; i++) {
    const it = items[i]
    if (it.type === 'ul' || it.type === 'ol') {
      const lis = []
      while (items[i + 1]?.type === 'li') lis.push(`<li>${inline(items[++i].text, prefix)}</li>`)
      out.push(`<${it.type}>${lis.join('')}</${it.type}>`)
    } else if (it.type === 'h2' || it.type === 'h3') {
      out.push(`<${it.type}>${esc(it.text)}</${it.type}>`)
    } else if (it.type === 'p') {
      out.push(`<p>${inline(it.text, prefix)}</p>`)
    } else if (it.type === 'quote') {
      out.push(`<blockquote><p>${esc(it.text)}</p></blockquote>`)
    }
  }
  return out.join('\n')
}

function build(post, lang) {
  const isAr = lang === 'ar'
  const path = isAr ? `/blog/${post.slug}` : `/en/blog/${post.slug}`
  const url = `${ORIGIN}${path}`
  const arUrl = `${ORIGIN}/blog/${post.slug}`
  const enUrl = `${ORIGIN}/en/blog/${post.slug}`
  const title = isAr ? post.titleAr : post.titleEn
  const desc = isAr ? post.descAr : post.descEn
  const metaTitle = isAr ? post.metaTitleAr : post.metaTitleEn
  const metaDesc = isAr ? post.metaDescAr : post.metaDescEn
  const content = isAr ? post.contentAr : post.contentEn
  for (const [k, v] of Object.entries({ title, desc, metaTitle, metaDesc })) {
    if (!v) throw new Error(`prerender: ${post.slug} (${lang}) ينقصه ${k}`)
  }

  const article = {
    '@context': 'https://schema.org', '@type': 'Article',
    headline: title, description: desc, image: `${ORIGIN}/og-image.png`,
    datePublished: post.date, dateModified: post.updated || post.date, inLanguage: lang,
    author: { '@type': 'Organization', name: 'Qaffel AI', url: ORIGIN },
    publisher: { '@type': 'Organization', name: 'Qaffel AI',
      logo: { '@type': 'ImageObject', url: `${ORIGIN}/brand/logo-icon-only.png` } },
    mainEntityOfPage: { '@type': 'WebPage', '@id': url },
  }
  const crumbs = [
    [isAr ? 'الرئيسية' : 'Home', isAr ? '/' : '/en'],
    [isAr ? 'المدونة' : 'Blog', isAr ? '/blog' : '/en/blog'],
    [title, path],
  ]
  const breadcrumb = {
    '@context': 'https://schema.org', '@type': 'BreadcrumbList',
    itemListElement: crumbs.map(([name, p], i) => ({
      '@type': 'ListItem', position: i + 1, name, item: `${ORIGIN}${p}`,
    })),
  }
  // `<` داخل JSON يُهرَّب لمنع إغلاق وسم script مبكراً
  const ld = (id, o) =>
    `<script type="application/ld+json" id="${id}">${JSON.stringify(o).replace(/</g, '\\u003c')}</script>`

  let h = template
  h = sub(h, /<html lang="ar" dir="rtl">/, `<html lang="${lang}" dir="${isAr ? 'rtl' : 'ltr'}">`, 'html lang')
  h = sub(h, /<title>[\s\S]*?<\/title>/, `<title>${esc(metaTitle)}</title>`, 'title')
  h = sub(h, /<meta name="description" content="[^"]*" \/>/,
    `<meta name="description" content="${esc(metaDesc)}" />`, 'meta description')
  h = sub(h, /<link rel="canonical" href="[^"]*" \/>/, `<link rel="canonical" href="${url}" />`, 'canonical')
  // كتلة hreflang الثلاثية — نفس ما يضبطه useSEO: ar + en + x-default(ar)
  h = sub(h, /<link rel="alternate" hreflang="ar"[^>]*>\s*<link rel="alternate" hreflang="en"[^>]*>\s*<link rel="alternate" hreflang="x-default"[^>]*>/,
    `<link rel="alternate" hreflang="ar" href="${arUrl}" />\n    <link rel="alternate" hreflang="en" href="${enUrl}" />\n    <link rel="alternate" hreflang="x-default" href="${arUrl}" />`, 'hreflang')
  h = sub(h, /<meta property="og:type" content="website" \/>/, '<meta property="og:type" content="article" />', 'og:type')
  h = sub(h, /<meta property="og:url" content="[^"]*" \/>/, `<meta property="og:url" content="${url}" />`, 'og:url')
  h = sub(h, /<meta property="og:title" content="[^"]*" \/>/, `<meta property="og:title" content="${esc(metaTitle)}" />`, 'og:title')
  h = sub(h, /<meta property="og:description" content="[^"]*" \/>/, `<meta property="og:description" content="${esc(metaDesc)}" />`, 'og:description')
  h = sub(h, /<meta property="og:locale" content="[^"]*" \/>/, `<meta property="og:locale" content="${isAr ? 'ar_SA' : 'en_US'}" />`, 'og:locale')
  h = sub(h, /<meta property="og:locale:alternate" content="[^"]*" \/>/, `<meta property="og:locale:alternate" content="${isAr ? 'en_US' : 'ar_SA'}" />`, 'og:locale:alternate')
  h = sub(h, /<meta name="twitter:title" content="[^"]*" \/>/, `<meta name="twitter:title" content="${esc(metaTitle)}" />`, 'twitter:title')
  h = sub(h, /<meta name="twitter:description" content="[^"]*" \/>/, `<meta name="twitter:description" content="${esc(metaDesc)}" />`, 'twitter:description')
  // ids مطابقة لـuseJsonLd ⇒ الكلاينت يحدّث نفس الوسم بدل ما يضيف نسخة ثانية
  h = sub(h, /<\/head>/, `${ld('ld-article', article)}\n    ${ld('ld-breadcrumb', breadcrumb)}\n  </head>`, 'head end')
  h = sub(h, /<div id="root"><\/div>/,
    `<div id="root"><article><p>${isAr ? 'نُشر' : 'Published'}: <time datetime="${post.date}">${post.date}</time>${post.updated && post.updated !== post.date ? ` · ${isAr ? 'آخر تحديث' : 'Last updated'}: <time datetime="${post.updated}">${post.updated}</time>` : ''}</p><h1>${esc(title)}</h1><p>${esc(desc)}</p>\n${renderBody(content, isAr ? '' : '/en')}</article></div>`, 'root')
  return { path, html: h }
}

for (const slug of TRIAL_SLUGS) {
  const post = BLOG_POSTS.find((p) => p.slug === slug)
  if (!post) throw new Error(`prerender: المقال ${slug} غير موجود بـblogPosts.js`)
  for (const lang of ['ar', 'en']) {
    const { path, html } = build(post, lang)
    const file = resolve(DIST, `.${path}.html`)
    mkdirSync(dirname(file), { recursive: true })
    writeFileSync(file, html)
    console.log(`prerender: ${path} → ${file.slice(DIST.length + 1)}`)
  }
}
