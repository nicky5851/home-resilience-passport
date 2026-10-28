import { SolarRoofStudioPage } from "@/features/studio/s05/SolarRoofStudioPage"

export default async function S05Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <SolarRoofStudioPage homeRef={ref} />
}
