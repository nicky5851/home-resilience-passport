import { CareCalendarPage } from "@/features/studio/s17/CareCalendarPage"

export default async function S17Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <CareCalendarPage homeRef={ref} />
}
