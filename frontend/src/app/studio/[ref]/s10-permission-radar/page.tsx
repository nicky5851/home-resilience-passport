import { PermissionRadarPage } from "@/features/studio/s10/PermissionRadarPage"

export default async function S10Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <PermissionRadarPage homeRef={ref} />
}
