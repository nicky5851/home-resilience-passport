import { DampMouldLabPage } from "@/features/studio/s11/DampMouldLabPage"

export default async function S11Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <DampMouldLabPage homeRef={ref} />
}
