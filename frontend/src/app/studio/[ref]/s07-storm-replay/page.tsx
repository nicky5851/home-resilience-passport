import { StormReplayPage } from "@/features/studio/s07/StormReplayPage"

export default async function S07Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <StormReplayPage homeRef={ref} />
}
