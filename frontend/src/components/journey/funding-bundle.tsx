import type { FundingBundle as FundingBundleType } from "@/lib/api/types"

const KIND_LABEL: Record<FundingBundleType["lines"][number]["option"]["kind"], string> = {
  grant: "Grant",
  cashback: "Cashback",
  insurance_discount: "Insurance discount",
  loan: "Loan",
  mortgage_further_advance: "Mortgage further advance",
}

const KIND_COLOR: Record<FundingBundleType["lines"][number]["option"]["kind"], string> = {
  grant: "bg-green",
  cashback: "bg-deep",
  insurance_discount: "bg-warning",
  loan: "bg-muted-foreground",
  mortgage_further_advance: "bg-muted-foreground",
}

/** The funding bundle (spec L12): stacked bar, one card per line, monthly cost. */
export function FundingBundleView({ bundle, cost }: { bundle: FundingBundleType; cost: number }) {
  const total = cost || 1

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-mint flex h-4 overflow-hidden rounded-full">
          {bundle.lines.map((line, i) => (
            <div
              key={i}
              className={KIND_COLOR[line.option.kind]}
              style={{ width: `${(line.amount_gbp / total) * 100}%` }}
              title={`${KIND_LABEL[line.option.kind]}: £${line.amount_gbp.toLocaleString()}`}
            />
          ))}
        </div>
        <div className="text-muted-foreground flex justify-between text-sm">
          <span>Covered: £{bundle.covered_gbp.toLocaleString()}</span>
          <span>Still needed: £{bundle.gap_gbp.toLocaleString()}</span>
        </div>
      </div>

      <ul className="space-y-3">
        {bundle.lines.map((line, i) => (
          <li key={i} className="border-border rounded-lg border p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium">
                {line.option.name}
                <span className="text-muted-foreground ml-2 text-sm">
                  ({KIND_LABEL[line.option.kind]})
                </span>
              </p>
              {line.option.is_mock && (
                <span className="bg-warning/15 text-warning rounded-full px-2 py-0.5 text-xs font-semibold">
                  Illustrative
                </span>
              )}
            </div>
            <p className="text-deep font-semibold">£{line.amount_gbp.toLocaleString()}</p>
            <p className="text-muted-foreground text-sm">{line.note}</p>
          </li>
        ))}
      </ul>

      {bundle.monthly_cost_gbp !== null && (
        <p className="text-deep text-lg font-semibold">
          Monthly cost for the rest: £{bundle.monthly_cost_gbp.toLocaleString()}
        </p>
      )}
    </div>
  )
}
