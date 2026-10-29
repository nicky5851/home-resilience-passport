import type { components } from "@/features/studio/api/schema"

export type FeatureMeta = components["schemas"]["FeatureMeta"]
export type StudioHomeSummary = components["schemas"]["StudioHomeSummary"]

export type HotspotId = components["schemas"]["Hotspot"]["id"]
export type Hotspot = components["schemas"]["Hotspot"]
export type SandboxMeasure = components["schemas"]["SandboxMeasure"]
export type SandboxState = components["schemas"]["SandboxState"]
export type SandboxInit = components["schemas"]["SandboxInit"]

export type StreetProof = components["schemas"]["StreetProof"]
export type Story = components["schemas"]["Story"]
export type UpgradeRow = components["schemas"]["UpgradeRow"]
export type BandCount = components["schemas"]["BandCount"]

export type Fingerprint = components["schemas"]["Fingerprint"]

export type HeatPumpYear = components["schemas"]["HeatPumpYear"]
export type MonthlyHeatPump = components["schemas"]["MonthlyHeatPump"]
export type DailyHeatPump = components["schemas"]["DailyHeatPump"]

export type SolarResult = components["schemas"]["SolarResult"]
export type OrientationPoint = components["schemas"]["OrientationPoint"]

export type GridCarbon = components["schemas"]["GridCarbon"]
export type BestWindow = components["schemas"]["BestWindow"]
export type ForecastSlot = components["schemas"]["ForecastSlot"]
export type MixShare = components["schemas"]["MixShare"]

export type StormReplayIndex = components["schemas"]["StormReplayIndex"]
export type Replay = components["schemas"]["Replay"]
export type EventSummary = components["schemas"]["EventSummary"]
export type HourlyReplayPoint = components["schemas"]["HourlyReplayPoint"]

export type FloodMemory = components["schemas"]["FloodMemory"]
export type FloodEvent = components["schemas"]["FloodEvent"]
export type DecadeCount = components["schemas"]["DecadeCount"]

export type Shoreline = components["schemas"]["Shoreline"]
export type Projection = components["schemas"]["Projection"]

export type PermissionRadar = components["schemas"]["PermissionRadar"]
export type Constraint = components["schemas"]["Constraint"]
export type MeasureVerdict = components["schemas"]["MeasureVerdict"]

export type DampLab = components["schemas"]["DampLab"]
export type DampLabRequest = components["schemas"]["DampLabRequest"]
export type SurfaceRisk = components["schemas"]["SurfaceRisk"]
