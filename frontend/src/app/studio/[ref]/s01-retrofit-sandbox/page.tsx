import { SandboxPage } from "@/features/studio/s01/SandboxPage"

export default async function S01Page({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params
  return <SandboxPage homeRef={ref} />
}
