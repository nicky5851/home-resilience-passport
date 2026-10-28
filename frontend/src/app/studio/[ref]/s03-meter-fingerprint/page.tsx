import { MeterFingerprintPage } from "@/features/studio/s03/MeterFingerprintPage"

export default async function S03Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <MeterFingerprintPage homeRef={ref} />
}
