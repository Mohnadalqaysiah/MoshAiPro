import { useEffect } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { useLang } from '../contexts/LangContext'
import { getPost, BLOG_POSTS } from '../data/blogPosts'
import { Clock, ChevronLeft, ChevronRight, Tag, ArrowLeft, ArrowRight } from 'lucide-react'
import useSEO from '../hooks/useSEO'
import useArticleSchema from '../hooks/useArticleSchema'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

// ── Render individual content block ─────────────────────────────────────────
function ContentBlock({ item }) {
  switch (item.type) {
    case 'h2':    return <h2 className="text-2xl font-black text-white mt-10 mb-4 leading-snug">{item.text}</h2>
    case 'h3':    return <h3 className="text-lg font-bold text-blue-300 mt-7 mb-3">{item.text}</h3>
    case 'p':     return <p className="text-gray-300 leading-relaxed mb-4">{item.text}</p>
    case 'ul':    return null   // container for li items — handled below
    case 'ol':    return null
    case 'li':    return (
      <li className="flex items-start gap-2.5 text-gray-300 mb-2">
        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
        <span>{item.text}</span>
      </li>
    )
    case 'quote': return (
      <blockquote className="my-6 border-s-4 border-blue-500 bg-blue-950/30 px-5 py-4 rounded-e-xl">
        <p className="text-blue-200 italic leading-relaxed">"{item.text}"</p>
      </blockquote>
    )
    default:      return null
  }
}

// ── Group consecutive li items into ul/ol containers ────────────────────────
function renderContent(items) {
  const out = []
  let i = 0
  while (i < items.length) {
    const item = items[i]
    if (item.type === 'ul' || item.type === 'ol') {
      const Tag = item.type === 'ul' ? 'ul' : 'ol'
      const lis = []
      i++
      while (i < items.length && items[i].type === 'li') {
        lis.push(<ContentBlock key={i} item={items[i]} />)
        i++
      }
      out.push(
        <Tag key={`list-${i}`} className={`ms-4 mb-4 space-y-1 ${item.type === 'ol' ? 'list-decimal list-inside' : ''}`}>
          {lis}
        </Tag>
      )
    } else {
      out.push(<ContentBlock key={i} item={item} />)
      i++
    }
  }
  return out
}

export default function BlogPost() {
  const { slug } = useParams()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const ChevronBtn = isAr ? ChevronLeft : ChevronRight
  const ArrowBack  = isAr ? ArrowRight  : ArrowLeft

  const post = getPost(slug)

  useSEO({
    title: post ? `${isAr ? post.titleAr : post.titleEn} | Qaffel AI Blog` : undefined,
    description: post ? (isAr ? post.descAr : post.descEn) : undefined,
  })
  useArticleSchema(post, isAr, `/blog/${slug}`)
  useBreadcrumbSchema(post ? [
    { name: isAr ? 'الرئيسية' : 'Home', path: '/' },
    { name: isAr ? 'المدونة' : 'Blog', path: '/blog' },
    { name: isAr ? post.titleAr : post.titleEn, path: `/blog/${slug}` },
  ] : null)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [post])

  if (!post) return <Navigate to="/blog" replace />

  const title   = isAr ? post.titleAr : post.titleEn
  const desc    = isAr ? post.descAr  : post.descEn
  const content = isAr ? post.contentAr : post.contentEn
  const cat     = isAr ? post.category.ar : post.category.en

  // Related posts (same category, exclude current)
  const related = BLOG_POSTS
    .filter(p => p.slug !== slug && p.category.ar === post.category.ar)
    .slice(0, 2)

  return (
    <div className="min-h-screen bg-[#070b14] text-white" dir={isAr ? 'rtl' : 'ltr'}>
      {/* ── Breadcrumb ── */}
      <div className="border-b border-white/5 bg-[#070b14]/80">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-2 text-sm text-gray-500 flex-wrap">
          <Link to="/" className="hover:text-blue-400 transition-colors">{isAr ? 'الرئيسية' : 'Home'}</Link>
          <ChevronBtn size={13} />
          <Link to="/blog" className="hover:text-blue-400 transition-colors">{isAr ? 'المدونة' : 'Blog'}</Link>
          <ChevronBtn size={13} />
          <span className="text-gray-400 truncate max-w-[200px]">{title}</span>
        </div>
      </div>

      <article className="max-w-3xl mx-auto px-4 py-12">
        {/* Back link */}
        <Link to="/blog"
          className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-blue-400 transition-colors mb-8">
          <ArrowBack size={15} />
          {isAr ? 'العودة للمدونة' : 'Back to Blog'}
        </Link>

        {/* Meta */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <span className="text-xs bg-blue-500/15 text-blue-300 border border-blue-500/20 px-3 py-1 rounded-full font-medium">
            {cat}
          </span>
          <span className="text-xs text-gray-600 flex items-center gap-1">
            <Clock size={11} />
            {post.readTime} {isAr ? 'دقائق قراءة' : 'min read'}
          </span>
          <span className="text-xs text-gray-600">
            {new Date(post.date).toLocaleDateString(isAr ? 'ar-SA' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-3xl md:text-4xl font-black text-white mb-5 leading-tight">
          {title}
        </h1>

        {/* Excerpt */}
        <p className="text-gray-400 text-lg leading-relaxed mb-8 border-b border-white/5 pb-8">
          {desc}
        </p>

        {/* Content */}
        <div className="prose-custom">
          {renderContent(content)}
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mt-10 pt-8 border-t border-white/5">
          {post.tags.map(tag => (
            <span key={tag} className="inline-flex items-center gap-1.5 text-xs text-gray-500 border border-white/8 px-3 py-1.5 rounded-lg hover:border-blue-500/30 hover:text-blue-400 transition-colors cursor-default">
              <Tag size={10} />
              {tag}
            </span>
          ))}
        </div>

        {/* CTA box */}
        <div className="mt-12 bg-gradient-to-br from-blue-950/50 to-indigo-950/30 border border-blue-500/20 rounded-2xl p-7 text-center">
          <p className="text-sm text-blue-300 font-semibold mb-1">
            {isAr ? '🤖 طبّق هذا التحليل تلقائياً' : '🤖 Apply This Analysis Automatically'}
          </p>
          <h3 className="text-xl font-black text-white mb-3">
            {isAr ? 'Qaffel AI يطبق ICT/SMC في ثوانٍ' : 'Qaffel AI Applies ICT/SMC in Seconds'}
          </h3>
          <p className="text-gray-400 text-sm mb-5">
            {isAr
              ? 'بدلاً من التحليل اليدوي — احصل على إشارة كاملة مع الدخول والوقف والأهداف مباشرة على Telegram'
              : 'Instead of manual analysis — get a complete signal with entry, SL, and TPs directly on Telegram'}
          </p>
          <Link to="/register"
            className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-8 py-3 rounded-xl font-bold transition-all hover:scale-105 shadow-lg shadow-blue-500/20 text-sm">
            {isAr ? 'ابدأ مجاناً — 10 تحليلات' : 'Start Free — 10 Analyses'}
            <ChevronBtn size={15} />
          </Link>
        </div>

        {/* Related posts */}
        {related.length > 0 && (
          <div className="mt-12">
            <h3 className="font-bold text-white mb-5 text-lg">
              {isAr ? 'مقالات ذات صلة' : 'Related Articles'}
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              {related.map(rp => (
                <Link key={rp.slug} to={`/blog/${rp.slug}`}
                  className="group flex flex-col border border-white/8 hover:border-blue-500/30 rounded-xl p-5 transition-all hover:-translate-y-0.5">
                  <span className="text-xs text-gray-600 mb-2 flex items-center gap-1">
                    <Clock size={10} /> {rp.readTime} {isAr ? 'دقائق' : 'min'}
                  </span>
                  <span className="font-bold text-sm text-gray-200 group-hover:text-blue-300 transition-colors line-clamp-2">
                    {isAr ? rp.titleAr : rp.titleEn}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </article>
    </div>
  )
}
