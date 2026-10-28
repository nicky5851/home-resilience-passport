import { Suspense } from "react"

import { AccountPage } from "./account-page"

export const metadata = { title: "Account · Home Resilience Passport" }

export default function Page() {
  return (
    <section className="max-w-xl space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Account</h1>
      <Suspense>
        <AccountPage />
      </Suspense>
    </section>
  )
}
