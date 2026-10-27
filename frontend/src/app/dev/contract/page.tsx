import { ContractRunner } from "./contract-runner"

export const metadata = { title: "Contract check · Home Resilience Passport" }

// Developer page: exercises every seam in docs/CONTRACT.md. Hidden in production from L15.
export default function ContractPage() {
  return (
    <section className="space-y-4">
      <h1 className="text-deep text-2xl font-semibold">Contract check</h1>
      <p className="text-muted-foreground text-sm">
        Calls every API seam in order and shows a tick per call. Run it against the stub API (
        <code>make dev</code>) and in mock mode (<code>NEXT_PUBLIC_API_MOCK=1 pnpm dev</code>).
      </p>
      <ContractRunner />
    </section>
  )
}
