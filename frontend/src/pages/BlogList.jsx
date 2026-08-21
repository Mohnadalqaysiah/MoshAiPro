import { Link } from 'react-router-dom'
import { useLang } from '../contexts/LangContext'
import { BLOG_POSTS } from '../data/blogPosts'
import { BookOpen, Clock, ChevronLeft, ChevronRight, Tag } from 'lucide-react'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

export default function BlogList() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const ChevronBtn = isAr ? ChevronLeft : ChevronRight

  useSEO({
    title: isAr
      ? 'مدونة Qaffel AI — تعلم تداول الذهب والفوركس بتقنية ICT/SMC'
      : 'Qaffel AI Blog — Learn ICT/SMC Gold & Forex Trading',
    description: isAr
      ? 'مقالات تعليمية في تداول الذهب XAUUSD، الفوركس، والكريبتو بمنهجية ICT/SMC. Order Blocks، FVG، Smart Money Concepts — مشروحة بالعربي.'
      : 'Educational articles on trading Gold XAUUSD, Forex, and Crypto using ICT/SMC methodology. Order Blocks, FVG, Smart Money Concepts explained.',
  })

  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: '/' },
    { name: isAr ? 'المدونة' : 'Blog', path: '/blog' },
  ], isAr)

  const sorted = [...BLOG_POSTS].sort((a, b) => new Date(b.date) - new Date(a.date))

  return (
    <div className="min-h-screen bg-[#070b14] text-white" dir={isAr ? 'rtl' : 'ltr'}>
      {/* ── Header ── */}
      <div className="border-b border-white/5 bg-[#070b14]/80">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3 text-sm text-gray-500">
          <Link to="/" className="hover:text-blue-400 transition-colors">
            {isAr ? 'الرئيسية' : 'Home'}
          </Link>
          <ChevronBtn size={14} />
          <span className="text-gray-300">{isAr ? 'المدونة' : 'Blog'}</span>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-16">
        {/* Hero */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-5">
            <BookOpen size={12} />
            {isAr ? 'تعلم الاحتراف' : 'Learn to Trade'}
          </div>
          <h1 className="text-3xl md:text-5xl font-black mb-5 leading-tight">
            {isAr
              ? <><span className="text-white">مدونة </span><span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">Qaffel AI</span></>
              : <><span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">Qaffel AI </span><span className="text-white">Blog</span></>
            }
          </h1>
          <p className="text-gray-400 max-w-xl mx-auto text-lg leading-relaxed">
            {isAr
              ? 'مقالات تعليمية احترافية في تداول الذهب والفوركس والكريبتو بمنهجية ICT/SMC'
              : 'Professional educational articles on Gold, Forex & Crypto trading using ICT/SMC methodology'}
          </p>
        </div>

        {/* Articles grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {sorted.map((post, i) => {
            const title = isAr ? post.titleAr : post.titleEn
            const desc  = isAr ? post.descAr  : post.descEn
            const cat   = isAr ? post.category.ar : post.category.en
            return (
              <Link key={post.slug} to={`/blog/${post.slug}`}
                className="group relative flex flex-col bg-gradient-to-br from-white/4 to-white/[0.01] border border-white/8 hover:border-blue-500/30 rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-blue-500/10">

                {/* Category + read time */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs bg-blue-500/15 text-blue-300 border border-blue-500/20 px-3 py-1 rounded-full font-medium">
                    {cat}
                  </span>
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Clock size={11} />
                    {post.readTime} {isAr ? 'دقائق' : 'min read'}
                  </span>
                </div>

                {/* Title */}
                <h2 className="text-lg font-bold text-white mb-3 leading-snug group-hover:text-blue-300 transition-colors line-clamp-2">
                  {title}
                </h2>

                {/* Excerpt */}
                <p className="text-gray-500 text-sm leading-relaxed line-clamp-3 flex-1 mb-4">
                  {desc}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {post.tags.slice(0, 3).map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1 text-xs text-gray-400 border border-white/6 px-2 py-0.5 rounded-lg">
                      <Tag size={9} />
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-4 border-t border-white/5">
                  <span className="text-xs text-gray-400">
                    {new Date(post.date).toLocaleDateString(isAr ? 'ar-SA' : 'en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                  </span>
                  <span className="text-xs text-blue-400 flex items-center gap-1 group-hover:gap-2 transition-all">
                    {isAr ? 'اقرأ المقال' : 'Read article'}
                    <ChevronBtn size={13} />
                  </span>
                </div>
              </Link>
            )
          })}
        </div>

        {/* CTA */}
        <div className="mt-16 text-center bg-gradient-to-br from-blue-950/40 to-indigo-950/20 border border-blue-500/15 rounded-2xl p-10">
          <h3 className="text-2xl font-black mb-3">
            {isAr ? 'طبّق ما تعلمته مجاناً' : 'Apply What You Learned — Free'}
          </h3>
          <p className="text-gray-400 mb-6">
            {isAr
              ? 'Qaffel AI يطبق كل هذه المفاهيم تلقائياً — احصل على 10 تحليلات مجانية الآن'
              : 'Qaffel AI applies all these concepts automatically — get 10 free analyses now'}
          </p>
          <Link to="/register"
            className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-8 py-3.5 rounded-xl font-bold transition-all hover:scale-105 shadow-lg shadow-blue-500/20">
            {isAr ? 'ابدأ مجاناً' : 'Start Free'}
            <ChevronBtn size={16} />
          </Link>
        </div>
      </div>
    </div>
  )
}
