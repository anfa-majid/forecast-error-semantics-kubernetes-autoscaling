# Step 15 Primary Experimental Execution — Framework Report

## Current status

The execution framework is commissioned offline. Final Kubernetes evidence has not yet been collected. Step 15 is complete only after all 132 frozen safety-disabled cells have valid archived attempts or transparent unresolved failure records.

## Frozen scope

- 112 matched-error runs (`phase=primary`).
- 20 oracle references (`phase=reference`).
- 132 total unique run cells.
- 10 safety-enabled rows are excluded and reserved for the secondary campaign.

## Execution controls

The manager enforces one active attempt, ascending filtered Step 14 order, explicit pause/resume, immutable attempt history, and same-cell replacement after technical invalidity. It does not expose outcome-based condition selection.

## Remaining commissioning work

The live Azure runner, preflight, and post-run adjudicator must be commissioned against one frozen cell before the campaign is resumed. No final run is valid merely because the load generator exits successfully; all frozen completeness rules must pass.
