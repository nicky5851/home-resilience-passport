import { StreetProofPage } from "@/features/studio/s02/StreetProofPage"

export default async function S02Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <StreetProofPage homeRef={ref} />
}
