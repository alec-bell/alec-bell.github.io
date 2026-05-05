import { Feed } from 'feed'
import { getAllArticles } from '@/lib/articles'

export const dynamic = 'force-static'

function getSiteUrl() {
  return (process.env.NEXT_PUBLIC_SITE_URL ?? 'https://example.com').replace(
    /\/$/,
    '',
  )
}

export async function GET() {
  let siteUrl = getSiteUrl()
  let articles = await getAllArticles()

  let author = {
    name: 'Spencer Sharp',
    email: 'spencer@planetaria.tech',
  }

  let feed = new Feed({
    title: author.name,
    description: 'Your blog description',
    author,
    id: siteUrl,
    link: siteUrl,
    image: `${siteUrl}/favicon.ico`,
    favicon: `${siteUrl}/favicon.ico`,
    copyright: `All rights reserved ${new Date().getFullYear()}`,
    feedLinks: {
      rss2: `${siteUrl}/feed.xml`,
    },
  })

  for (let article of articles) {
    let publicUrl = `${siteUrl}/articles/${article.slug}`
    feed.addItem({
      title: article.title,
      id: publicUrl,
      link: publicUrl,
      description: article.description,
      author: [author],
      contributor: [author],
      date: new Date(article.date),
    })
  }

  return new Response(feed.rss2(), {
    status: 200,
    headers: {
      'content-type': 'application/xml',
      'cache-control': 's-maxage=31556952',
    },
  })
}
