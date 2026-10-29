import { GreenValueLensPage } from "@/features/studio/s14/GreenValueLensPage"

export default async function S14Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <GreenValueLensPage homeRef={ref} />
}
