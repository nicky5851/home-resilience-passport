import { PublicPassportView } from "./public-passport-view"

export const metadata = { title: "Shared passport · Home Resilience Passport" }

export default async function PublicPassportPage({
  params,
}: {
  params: Promise<{ token: string }>
}) {
  const { token } = await params
  return (
    <section className="space-y-6">
      <PublicPassportView token={token} />
    </section>
  )
}
