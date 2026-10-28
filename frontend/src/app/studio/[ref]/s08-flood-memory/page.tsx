import { FloodMemoryPage } from "@/features/studio/s08/FloodMemoryPage"

export default async function S08Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <FloodMemoryPage homeRef={ref} />
}
