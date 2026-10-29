import { WeekAheadPage } from "@/features/studio/s16/WeekAheadPage"

export default async function S16Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <WeekAheadPage homeRef={ref} />
}
