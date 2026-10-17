// (2026-10-17) يولّد dist/llms.txt وقت البناء (معيار llmstxt.org: Markdown، عنوان H1، ملخص، روابط).
// يُشتق من blogPosts.js فيبقى محدّثاً تلقائياً مع كل مقال جديد. بدونه كان /llms.txt يرجّع صفحة الـSPA (HTML).
import { writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const O = 'https://qaffel.com'
const { BLOG_POSTS } = await import(pathToFileURL(resolve(ROOT, 'src/data/blogPosts.js')).href)

const pages = [
  ['Home (Arabic)', '/', 'AI-assisted ICT/SMC technical analysis platform for gold, crypto, forex, US indices and Gulf stocks, with Telegram alerts.'],
  ['Home (English)', '/en', 'English version of the home page.'],
  ['Pricing', '/en/pricing', 'Free trial, weekly, monthly and yearly plans.'],
  ['Strategy Builder', '/en/strategy-builder', 'Build a no-code strategy from ICT/SMC conditions and receive Telegram alerts when it triggers.'],
  ['About', '/en/about', 'Who we are and what the platform offers.'],
  ['Vision', '/en/vision', 'Vision, mission and roadmap.'],
  ['Referral program', '/en/referral', 'Commission on payments from referred subscribers.'],
  ['Learning games', '/games/challenge', 'Free interactive trading-education games.'],
  ['Contact', '/en/contact', 'Support by email and Telegram.'],
]

const out = [
  '# Qaffel AI',
  '',
  '> Qaffel AI (كفيل) is an Arabic-first platform that applies ICT / Smart Money Concepts technical analysis with AI to gold (XAUUSD), crypto, forex, US indices and Gulf stocks, and delivers complete trade plans (entry, stop-loss, targets, position size) via Telegram. Content is educational technical analysis, not financial advice; trading carries high risk.',
  '',
  'Every page exists in Arabic (default) and English (/en prefix).',
  '',
  '## Main pages',
  '',
  ...pages.map(([t, p, d]) => `- [${t}](${O}${p}): ${d}`),
  '',
  '## Articles',
  '',
  ...BLOG_POSTS.map((p) => `- [${p.titleEn}](${O}/en/blog/${p.slug}): ${p.metaDescEn || p.descEn}`),
  '',
  '## Legal',
  '',
  `- [Terms](${O}/en/terms)`,
  `- [Privacy policy](${O}/en/privacy)`,
  '',
]
writeFileSync(resolve(ROOT, 'dist/llms.txt'), out.join('\n'))
console.log(`llms.txt: ${BLOG_POSTS.length} articles`)
