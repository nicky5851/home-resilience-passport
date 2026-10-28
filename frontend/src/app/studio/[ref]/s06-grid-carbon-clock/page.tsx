import { GridCarbonClockPage } from "@/features/studio/s06/GridCarbonClockPage"

export default async function S06Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <GridCarbonClockPage homeRef={ref} />
}
