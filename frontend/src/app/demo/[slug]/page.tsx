import { DemoHomeView } from "./demo-home-view"

export const metadata = { title: "Demo home · Home Resilience Passport" }

export default async function DemoHomePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  return (
    <section className="space-y-6">
      <DemoHomeView slug={slug} />
    </section>
  )
}
