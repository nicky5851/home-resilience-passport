import { HeatPumpYearPage } from "@/features/studio/s04/HeatPumpYearPage"

export default async function S04Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <HeatPumpYearPage homeRef={ref} />
}
