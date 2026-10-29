import { BreatheEasyPage } from "@/features/studio/s12/BreatheEasyPage"

export default async function S12Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <BreatheEasyPage homeRef={ref} />
}
