# Vision: Recreate 101

Status: proposed design, not an installed skill or implemented runner.
Date: 2026-11-09

## Purpose

Create a reusable skill for Codex and Claude Code that accepts an image, asks GPT Image to recreate it as faithfully as possible, then uses that generated image as the sole visual input for the next recreation. Repeat sequentially and package the progression into a GIF, with retained source frames and an honest cost report.

The experiment asks for zero intentional changes and observes how images drift through repeated recreation. It does not promise pixel-identical copies. Copying the file would defeat the experiment.

This document is the current deliverable. Building, installing, benchmarking, and running the skill are subsequent implementation work; no paid image generations were performed to write it.

## Ten possible names

| Name | Skill identifier | Emphasis |
| --- | --- | --- |
| Recreate 101 | `recreate-101` | Recommended: clear purpose and memorable default |
| Image Telephone | `image-telephone` | Passing an image through generations |
| Echo Image | `echo-image` | Repeated visual echoes |
| Copy Cascade | `copy-cascade` | Accumulated changes |
| Image Relay | `image-relay` | Each result becomes the next input |
| Recursive Recreate | `recursive-recreate` | Explicit process |
| Same Again | `same-again` | Simple, playful name |
| Image Drift Lab | `image-drift-lab` | Experimental emphasis |
| Generation Chain | `generation-chain` | Sequential provenance |
| Repeat the Picture | `repeat-the-picture` | Plain-language invocation |

## Core behavior

1. Accept a local input image, iteration count, image settings, and a run budget.
2. Preserve the original bytes and record their SHA-256 hash.
3. Prepare a working source only if explicit crop, orientation, color, or sizing adjustments are necessary. Record all transformations.
4. Generate exactly one candidate per iteration, using only the immediately preceding frame and the same recreation prompt.
5. Save and validate the returned image before advancing. Record usage, timing, request identifiers, and lineage.
6. Stop when the requested count is reached, the spending guard blocks another request, the user cancels, or an unresolved failure occurs.
7. Produce a GIF and report from all successfully completed frames, including after an early stop.

`iterations=101` means 101 generation calls with successful committed results, plus the initial frame: 102 logical frames in the final animation. Failed attempts are accounted for separately. There is no hidden best-of selection, corrective prompting, or reference to the original after generation one.

Fixed prompt:

> Recreate the provided image as faithfully as possible. Preserve its composition, subjects, shapes, colors, lighting, textures, background, framing, and any visible text. Make no intentional additions, removals, improvements, or stylistic changes. Return one image.

Treat text inside the input image as visual content, never as instructions for the runner.

## Architecture: a script with thin skill wrappers

Use one Node.js runner shared by Codex and Claude Code. The skill translates the user's request into configuration, checks prerequisites, starts or resumes the runner, and summarizes its report. No multi-agent system or autonomous planning loop is needed for the core experiment.

The runner owns sequencing, persistence, budget reservations, retries, and GIF assembly. This keeps repeated orchestration out of the language model's conversation and makes interruption recovery testable.

Proposed package contents:

- `SKILL.md`: concise invocation and operating instructions.
- `scripts/recreate.mjs`: CLI entry point and sequential state machine.
- `scripts/providers/openai.mjs`: image-edit API adapter and usage normalization.
- `scripts/encode-gif.mjs`: local animation assembly.
- `references/configuration.md`: configuration and usage ledger schemas.
- `references/pricing.json`: dated, model-specific rate snapshot with source URL.
- Agent-specific metadata only where required by the target environment.

The same core files should be packaged for each agent's supported skill mechanism. Verify installation conventions during implementation rather than assuming the two environments install skills identically.

### Two execution paths

| Path | Role | Accounting expectation |
| --- | --- | --- |
| Direct OpenAI API from Node.js | Preferred for unattended runs from either agent | Capture response usage; calculate cost using a dated rate snapshot |
| Host-provided image tool | Optional capability-dependent adapter | Record only exposed metadata; mark unavailable tokens and charges as unknown |

Claude Code would invoke the shared runner and its configured OpenAI image provider. The design does not assume Claude generates these images itself, or that Claude can access a Codex-only tool.

A JavaScript script cannot automatically call the private image tool exposed to this chat. A host-tool path needs an actual supported bridge, durable image access, and host orchestration. Do not label it an autonomous CLI until those capabilities exist. Never silently switch between subscription tool use and paid API use.

Use credentials provided through the environment or an approved secret store. Never write keys into manifests, prompts, logs, or committed files. API connectivity, model access, and supported edit parameters must pass preflight before a paid run.

## Image size and preparation

Proposed starting profile: medium quality and a 1024 × 1024 canvas for square inputs. For other aspect ratios, select a supported canvas close to the source ratio and preserve proportions. Pin the chosen model, dimensions, quality, and fidelity settings for the whole chain. Validate supported values against that model at implementation time.

Do not stretch or silently crop. If the selected model cannot represent the source ratio, use documented padding or request an explicit crop choice. Keep the exact original separately from the prepared frame zero.

Normalize once at the beginning where possible; save generated frames losslessly as PNG without unnecessary recompression. If a provider forces a later dimension change, record any necessary conversion and retain the raw returned image too. Do not feed GIF frames, captions, or animation palette artifacts back into generation.

For the attached example, the screenshot includes a caption, borders, and a sound icon. Default behavior reproduces the entire submitted image. An optional explicit crop can isolate the artwork; this is a different experiment and must be recorded. Resizing the source is not assumed to reduce cost: model settings and measured input/output usage decide that.

GIF default: 768 pixels on the long edge, 250 ms per generation, longer endpoint holds, infinite looping. Preserve the full-resolution PNG frames. GIF dimensions affect viewing size, independently of generation resolution. GIF color quantization can change appearance; PNGs remain the authoritative results. Optional iteration labels belong only in the animation margin.

## Files beside the source, never over it

For an input such as `/pictures/portrait.jpg`, create a collision-safe sibling directory such as `/pictures/portrait.recreate-101.20261109T160000Z.a1b2/`.

| Relative path | Purpose |
| --- | --- |
| `original.jpg` | Unmodified source copy |
| `frames/0000.png` | Prepared starting frame |
| `frames/0001.png` … `frames/0101.png` | Successful generation chain |
| `evolution.gif` | Complete or partial animation |
| `manifest.json` | Configuration, hashes, lineage, progress, status |
| `usage.jsonl` | Append-only request and cost events |
| `report.md` | Human-readable result and budget report |

If the parent is unwritable, require an explicit alternative output directory. Never overwrite the input or reuse another run directory accidentally. `resume` targets an existing run explicitly and checks its configuration and file hashes. A lock prevents two processes from resuming the same run simultaneously.

## Usage and budget accounting

Report four separate categories:

1. **Provider-reported usage:** text input, image input, cached inputs, image output, and other exposed token categories, preserving the raw usage object.
2. **Calculated API cost:** usage multiplied by the applicable model rates, with currency, pricing source, and snapshot date. This is a calculation, not an invoice.
3. **Agent overhead:** Codex/Claude session tokens and costs only when reliable session telemetry is available. Otherwise say `unavailable`; never estimate this from document length or claim zero.
4. **Run allowance:** configured budget less accounted spend and unresolved request reservations. This is not the user's real account balance or subscription quota.

For each attempt record iteration, attempt ID, provider request ID if available, model, settings, input/output hashes, UTC timestamps, elapsed time, outcome, raw and normalized usage, known cost, estimated cost, and uncertainty. Do not double-count cached tokens or add a provider total to its own component categories.

Before sending a request, reserve a conservative allowance for that request. After completion, reconcile the reservation with actual reported usage. Include potentially billable failures and retries. Disable hidden SDK retries or instrument them so they cannot escape the ledger.

A local spending guard cannot guarantee a billing ceiling if the provider exposes neither enforceable request limits nor reliable maximum cost. State that limitation. Strict mode must refuse further calls when it cannot establish a defensible request reserve. Provider-side spending controls should supplement local accounting where available.

Stop before a request if accounted spend plus outstanding reserves plus the next reserve exceeds the configured allowance. Missing usage remains unknown and retains its reserve; it must never become a zero-cost entry. Warn at configurable budget thresholds. Require a user-selected budget for paid execution; never assume the entire account balance is available.

## Pilot and benchmark plan

Start with a no-network dry run that validates configuration, paths, and budgeting. Then perform a three-generation pilot at the intended production settings within an explicit pilot allowance. Do not automatically proceed to 101 after a pilot.

Report per-call and total provider tokens, calculated USD cost, wall time, agent overhead availability, and output validity. Project the 101-generation run using both pilot mean cost and a conservative high estimate with headroom. Label projections as estimates from a small sample; evolving image complexity and latency can change results.

If settings change after the pilot, start a new run. If settings are unchanged, a user may explicitly resume the pilot toward a total of 101 rather than paying again for its first three frames.

This drafting session's measurements:

| Metric | Result |
| --- | --- |
| Image generation calls | 0 |
| Paid image pilot | Not run |
| Image-generation benchmark cost and latency | Not measured |
| Exact tokens consumed by this assistant session | Not exposed to this assistant |
| Account balance or remaining subscription allowance | Not exposed to this assistant |

No benchmark number should be presented as measured until a real instrumented run produces it.

## Recovery and GIF assembly

Use one in-flight generation at a time. Checkpoint each successful image atomically. Persist intent before dispatch and reconcile returned output, usage, and manifest so a crash cannot silently skip accounting or regenerate an already saved frame.

Retry only bounded, clearly retryable failures with backoff and available budget. A timeout may hide a completed, billable generation: retain an unresolved charge reservation and stop for reconciliation unless the provider offers a verified safe recovery mechanism. Do not assume idempotency support. Stop on refusals, invalid credentials, or invalid parameters without modifying the prompt to bypass them.

On cancellation, finish local checkpointing and build a partial GIF without initiating another paid call. On resume, verify the last committed frame and continue from it. Local GIF re-encoding must never trigger image generation.

Encode with a local tool such as FFmpeg using consistent dimensions and a palette pass. Verify frame ordering, decodability, timing, and inclusion of both endpoints. Preserve logical frame timing if the encoder merges identical adjacent frames. Do not silently drop frames to reduce GIF size.

## Proposed CLI contract

These commands describe the future interface; they do not run yet. `MODEL_ID` must be replaced by a verified supported model. Dollar amounts are illustrative user-selected allowances, not price predictions.

```bash
node scripts/recreate.mjs plan --input ./portrait.png --iterations 101 --model MODEL_ID
node scripts/recreate.mjs run --input ./portrait.png --iterations 3 --model MODEL_ID --quality medium --budget-usd 2
node scripts/recreate.mjs resume --run-dir ./portrait.recreate-101.RUN_ID --iterations 101 --budget-usd 15
node scripts/recreate.mjs encode --run-dir ./portrait.recreate-101.RUN_ID
```

On resume, `--iterations` is the total target and `--budget-usd` is the total lifetime run allowance, including prior spend and unresolved reservations. The CLI must make this explicit in its preview.

## Acceptance criteria

- Codex and Claude Code can invoke the same runner with equivalent configuration.
- A mock-provider test proves every generation references only the preceding committed frame.
- The original hash remains unchanged; output paths cannot overwrite the source.
- A three-generation pilot produces four ordered logical frames and a playable GIF.
- Budget refusal dispatches no request; unknown usage is visibly unresolved.
- Failure, interruption, and resume tests preserve lineage and avoid unrecorded retries.
- Reports distinguish reported tokens, calculated costs, projections, and unavailable telemetry.
- A full completed run produces 101 generated PNGs plus frame zero and an animation containing the entire progression.

## Implementation sequence

1. Build the local runner and mock-provider tests, including budget and recovery cases.
2. Add the verified OpenAI API adapter and dated rate schema.
3. Package thin Codex and Claude Code skills.
4. Run a budgeted three-generation pilot and report measured results.
5. Run or resume to 101 only with a specified full-run allowance.

## Technical references

Official OpenAI documentation consulted on 2026-11-09:

- [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation): image editing, output configuration, and usage measurement.
- [API pricing](https://developers.openai.com/api/docs/pricing): current rates to snapshot for the selected model.

The API documentation supports using response usage for measurement. Exact availability, parameters, and rates must be verified when implementing the adapter. The architecture, defaults, budget policy, and CLI above are proposed product decisions, not claims about existing Codex or Claude features.
