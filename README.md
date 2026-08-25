# librelane-action

Takes a student's RTL to a **GDSII** in GitHub Actions, so a first-year with a Chromebook and
no Docker can still finish the digital track.

Built because [decision D5](../../planning/decisions.md) put TinyTapeout out of scope, which
removed the only browser-only route to a GDSII and left charter outcome #2 — *"students will
have generated GDSII files for designs of their own choosing"* — sitting behind a 20 GB Docker
install.

This is **not** TinyTapeout, not a shuttle, and not a hosted abstraction. It is the same
LibreLane, on the same `config.json` the student would run locally, on someone else's computer.

## Use it

Copy [`templates/harden.yml`](templates/harden.yml) into your course repo as
`.github/workflows/harden.yml` and point it at your design:

```yaml
jobs:
  harden:
    uses: uoftasic/librelane-action/.github/workflows/harden.yml@main
    with:
      design-dir: labs/lab-05-elevator
```

Push. Open the **Actions** tab. You get:

- a job summary with your cell count, die area, timing slack, and the three sign-off checks
- a **chip-…** artifact holding your `.gds`, a KLayout render of it, `metrics.json`, and the
  gate-level netlist

Free and unmetered on public repos.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `design-dir` | *required* | Directory holding `config.json` |
| `config` | `config.json` | Config filename within that directory |
| `pdk-version` | `7b70722e…` | open_pdks commit; defaults to the workbench's build |

## It fails loudly on an unpinned PDK

`scripts/check_config.py` refuses to run a config without an explicit
`"PDK": "sky130A"`. This is deliberate. Without that key LibreLane inherits whatever the
environment defaults to — in the workbench, `ihp-sg13g2` — and then **succeeds**, handing back a
chip in the wrong technology with no error anywhere. It is the nastiest failure in the flow
because nothing goes red. So we make it go red here.

## What it cannot promise: identical results

The Action runs `ghcr.io/librelane/librelane:3.0.2`, the same LibreLane version as the
workbench, with the same pinned PDK. **The chips still come out about 1.7 % apart.**

| | Workbench | This Action |
|---|---|---|
| die area | 1616.79 µm² | 1644.49 µm² |
| DRC / LVS / antenna | 0 / 0 / 0 | 0 / 0 / 0 |

Both are clean. They are just not the same chip, because **LibreLane pins itself but not the
tools it drives**:

| Tool | Workbench | This Action |
|---|---|---|
| Yosys | 0.64 | 0.62 |
| OpenROAD | `26Q2-254-g61932e897` | `dcf36133a369…` |
| Magic | 8.3.636 | 8.3.623 |

We could close the gap by running the 16 GB workbench image instead, but Actions does not cache
`container:` pulls, so that pull would dominate every run.

Instead the job summary prints both version sets next to the student's numbers, and says why
they differ. **Lab expected-results must therefore be ballparks with a tolerance, never exact
figures** — otherwise the student who used CI thinks they broke something.

It is also a true and useful lesson: same source, same flow version, one different tool build,
measurably different chip. That is why a real tapeout pins every tool by hash.

## Layout

| Path | What |
|---|---|
| `.github/workflows/harden.yml` | the reusable workflow |
| `templates/harden.yml` | what a student copies into their repo |
| `scripts/check_config.py` | refuses an unpinned PDK, with an explanation |
| `scripts/summarise.py` | writes the job summary; runs on failure too |

## Verified on a real runner

Run [32909788285](https://github.com/vproHacks/librelane-action/actions/runs/32909788285),
`ubuntu-latest`, cold cache:

| | |
|---|---|
| Total wall clock | **231 s** (includes the first-time ~2 GB PDK download) |
| Cells placed | 107 |
| Die area | 1644.49 µm² |
| Setup slack | +13.61 ns |
| DRC / LVS / antenna | **0 / 0 / 0** |
| Artifact | 221 KB — GDS, render PNG, metrics, gate netlist, flow log |

Cached runs skip the PDK download.

### Why it does not use `container:`

The first attempt ran the job *inside* the LibreLane image and failed immediately:

```
exec /__e/node24/bin/node: no such file or directory
```

The image is nix-based and has no dynamic loader where the runner expects one, so the runner's
bundled Node cannot execute inside it — which breaks **every** JavaScript action:
`checkout`, `cache`, `upload-artifact`.

So the job runs on a normal runner and shells into the image with `docker run` for exactly the
step that needs it. Anyone tempted to "simplify" this back to `container:` should read this
paragraph first.

## Before this ships

- [ ] Move to `uoftasic/librelane-action` (the `action-repo` input already defaults there)
- [ ] Re-run the self-test once it is under the org, since `action-repo` will resolve differently
- [ ] Decide the artifact retention window (currently 30 days)
- [ ] Decide whether a failing sign-off check should fail the job, or just report — currently it
      reports, on the grounds that a student learning from a violated chip is better served by a
      readable summary than a red X
