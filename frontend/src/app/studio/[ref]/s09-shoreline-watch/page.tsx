import { ShorelineWatchPage } from "@/features/studio/s09/ShorelineWatchPage"

export default async function S09Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <ShorelineWatchPage homeRef={ref} />
}
