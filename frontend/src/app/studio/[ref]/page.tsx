import { StudioHomeHub } from "@/features/studio/studio-home-hub"

export default async function StudioHomePage({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <StudioHomeHub homeRef={ref} />
}
