import { AffordabilityStressTestPage } from "@/features/studio/s13/AffordabilityStressTestPage"

export default async function S13Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <AffordabilityStressTestPage homeRef={ref} />
}
