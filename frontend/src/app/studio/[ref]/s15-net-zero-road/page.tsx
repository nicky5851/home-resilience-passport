import { NetZeroRoadPage } from "@/features/studio/s15/NetZeroRoadPage"

export default async function S15Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <NetZeroRoadPage homeRef={ref} />
}
