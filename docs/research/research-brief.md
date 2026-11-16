# Research brief: Stages 1–3

Project: CNC machine automation, solo, software-only, zero budget.
Date: 16 Nov 2026. Status: awaiting approval of the recommended idea. Nothing has been built.

## 1. How this was produced

Four separate agents ran, each without seeing the others' output until consolidation.

| Agent | Scope | Output |
|---|---|---|
| Research | Tool wear, anomaly detection, quality, uncertainty, energy | 15 papers, 9 datasets, 5 gaps, 3 ideas |
| Manufacturing and architecture | G-code verification, time and energy estimation, interoperability, digital twins | 13 papers, open tools, shop workflow, 5 gaps, 3 ideas |
| Commercial | Products, pricing, SME evidence, patents | Product map, 9 patents, 3 ideas |
| Independent critic and novelty reviewer | Attack all 10 candidates, search for prior art that removes the novelty | Verdicts, prior-art table, data feasibility |

I ran the Scopus searches myself in your signed-in browser and did the consolidation, scoring and recommendation. The novelty review and the critic were one agent, not two.

## 2. Search log

### 2.1 Scopus (advanced search, run 16 Nov 2026, institutional session)

No filters were applied beyond the query text. Results were read from the first page, sorted as noted.

| # | Query | Sort | Hits |
|---|---|---|---|
| Q1 | `TITLE-ABS-KEY(("CNC" OR "machine tool" OR milling) AND ("G-code" OR "NC program") AND (verification OR "error detection" OR "large language model")) AND PUBYEAR > 2020` | Citations | 26 |
| Q2 | `TITLE-ABS-KEY(("machining time" OR "cycle time") AND (estimation OR prediction) AND ("NC program" OR "G-code" OR "NC code")) AND PUBYEAR > 2018` | Citations | 15 |
| Q3 | `TITLE-ABS-KEY("tool wear" AND (milling OR CNC) AND ("domain generalization" OR "cross-domain" OR "domain shift" OR "leave-one")) AND PUBYEAR > 2020` | Citations | 37 |
| Q4 | `TITLE-ABS-KEY("energy consumption" AND (prediction OR estimation) AND ("NC program" OR "G-code" OR "NC code") AND (machining OR milling OR "machine tool")) AND PUBYEAR > 2018` | Citations | 14 |
| Q5 | `TITLE-ABS-KEY(("tool wear" OR "remaining useful life") AND (milling OR machining) AND ("conformal prediction" OR "uncertainty quantification" OR "data leakage")) AND PUBYEAR > 2020` | Citations | 22 |
| Q6 | `TITLE-ABS-KEY(("G-code" OR "NC program" OR "NC code") AND (CNC OR milling OR "machine tool") AND (benchmark OR dataset OR corpus OR "static analysis" OR "fault injection" OR "anomaly detection")) AND PUBYEAR > 2020` | Newest | 29 |
| Q7 | `TITLE-ABS-KEY("conformal prediction" AND (machining OR milling OR CNC OR "machine tool"))` | Citations | 4 |
| Q8 | DOI query for 20 DOIs supplied by the research agents | Newest | 20 |
| Q9 | `REF("Multivariate time series data of milling processes with varying tool wear and machine tools")` | Newest | 19 |
| Q10 | `TITLE-ABS-KEY("tool wear" AND ("cross-machine" OR "different machine tools" OR "across machines" OR "leave-one-machine")) AND PUBYEAR > 2020` | Newest | 12 |

What this does and does not establish:

- Q8 returned 20 documents for 20 DOIs. I read the count, not each row.
- I read only the first 10 results of each query. Later pages were not screened.
- Q7 found four documents with "conformal prediction" and a machining term. One is about forestry, one about roughness, one about tool wear, one about maintenance scheduling. None is about machining time or energy. This is one query, so it is evidence of a thin area and not proof of absence.
- Q9 corrected the critic agent, which had reported no prior uses of the Denkena wear dataset. Scopus lists 19 citing documents, including a 2026 conference paper on cross-machine probabilistic wear prediction.

### 2.2 Open web

The agents used web search and opened publisher, arXiv, repository, vendor and Google Patents pages. Anything they could not open is marked NOT VERIFIED in their reports and is left out of the matrix or flagged there. Screening criteria: 2021–2026 emphasis, CNC or milling relevance, empirical or review work, a page that could be opened.

### 2.3 Remaining gaps in verification

- 17 matrix rows are Scopus records only (title, source, year). Their methods and results have not been read.
- Preprints and three conference items were not checked in Scopus.
- No full-text PDFs were downloaded through the library.

## 3. Opportunity map

| Area | Industrial pain | Existing approaches | Gap found | Data needed | Measurable outcome |
|---|---|---|---|---|---|
| A. Time and energy estimation from the NC program | CAM time estimates ignore real feedrate behaviour; quotes and schedules are built on them; per-part energy is rarely known | ML on G-code features, hybrid simulation plus ML, controller-side lag correction (Fanuc patents) | Models are single-machine and give point values. One paper reports large errors on unseen parts. No calibrated ranges found for time or energy | NC programs with measured signals. Two open KIT sets exist, CC BY 4.0, two machines | Time and energy error on unseen parts; interval coverage; runs needed to calibrate a new machine |
| B. Tool wear across machines | Tools are changed early or by feel | Deep models on force and vibration, domain adaptation | Results are not comparable across studies; cross-machine work exists but coverage under machine shift is rarely reported | Denkena set, 3 machines, 9 tools, CC BY 4.0 | Wear error and coverage on a held-out machine; controller-only vs dynamometer accuracy |
| C. NC program checking | Errors are found on the machine during prove-out | Full simulators (Vericut class), CAM simulation, early LLM checkers | No open CNC milling corpus or seeded-fault benchmark found | None exists; would be synthetic | Precision and recall on a fault taxonomy |
| D. Process anomaly detection against an expected signal | Scrap and tool breakage in unattended runs | Teach-in limits, vendor load monitors, learned reference signals | Only 15 labelled anomalous runs in the open data; no quantitative benchmark | KIT multimodal sets | Detection rate on unseen geometry, with wide confidence intervals |
| E. Monitoring and scheduling from machine state | Low utilisation, schedules that ignore machine state | Commercial monitoring priced per machine per month | No open real-shop traces; mostly integration work | Simulators with random values | Weak; no credible experiment |

Commercial evidence used here, with its quality:

- Monitoring is sold per machine per month (FourJaw publishes £72–180 plus a £200 device). Several vendors publish no prices.
- An independent US survey (Wipfli 2024, 335 firms) names lack of expertise (61 %) and cost (54 %) as the top barriers to adoption.
- India-specific adoption numbers were not found. Utilisation figures of 30–50 % come from one Indian vendor and are unverified.
- No independent figures were found for tool-breakage cost or programming bottlenecks.

## 4. Candidate portfolio and critique

| # | Candidate | Critic's strongest objection | Verdict |
|---|---|---|---|
| 1 | G-code pre-flight linter with seeded-fault benchmark | Faults you inject yourself make the evaluation circular | Keep, reframed |
| 2 | NC program to time and energy with calibrated ranges, cross-part and cross-machine | Point prediction is already done by the dataset authors; only about 87 jobs | Keep, narrowed |
| 3 | Cross-machine tool wear advisor with calibrated intervals | Nine tools are the independent units, and wear labels are mostly interpolated | Keep |
| 4 | Leakage-aware re-benchmark of the Bosch dataset | Meta-study with no method | Drop |
| 5 | Controller-signals-only wear monitoring | Incremental on its own | Merge into 3 |
| 6 | MTConnect/OPC UA replay dashboard with rescheduling | Integration work, no testable claim | Drop |
| 7 | Log-based OEE for legacy machines | No open data | Drop |
| 8 | Anomaly detection against an NC-conditioned expected signal | 15 anomalous runs cannot support a metric | Merge into 2 as a demo |
| 9 | LLM G-code benchmark | Will date quickly; no corpus | Merge into 1 as a baseline |
| 10 | Force-aware feed optimisation in simulation | Cannot be validated without a machine | Drop |

Shortlist: 2 (with 8), 3 (with 5), 1 (with 9).

## 5. Validation of the shortlist

### Idea 2: NC pre-flight estimator

- **Already known:** energy and power can be predicted from G-code on one machine (matrix rows 1–7); cycle time can be corrected with learned feedrate behaviour (rows 8–10); the KIT group predicts axis signals from NC code and has validated on both of its machines.
- **Potential contribution within the reviewed scope:** per-job and per-segment prediction intervals for time and drive energy with measured coverage on unseen part geometries, and a measured answer to how many runs a new machine needs before the intervals are valid.
- **Evidence for the distinction:** Q7 found no conformal work on machining time or energy; the critic found none in three searches; the closest paper states that generalisation to unseen parts is not yet achieved.
- **Uncertain:** the KIT group is active on the same data and could publish this. About 87 jobs limits how precisely coverage can be shown. The measured quantity is drive power from the controller, not wall-plug kWh.
- **Hypothesis:** on unseen part geometries, group-wise conformal intervals reach their nominal coverage within sampling error, where a point model with a fixed error margin does not; fewer than ten calibration runs restore coverage on the second machine.

### Idea 3: Cross-machine wear advisor

- **Already known:** cross-machine and unseen-machine wear models exist (rows 14–16), including one probabilistic cross-machine paper that cites the same dataset.
- **Potential contribution:** coverage of wear intervals on a held-out machine with tool-level calibration, and the accuracy lost when only controller signals are used.
- **Uncertain:** novelty is narrower than the critic assumed, because of row 14. Nine tools give few independent units.
- **Hypothesis:** intervals calibrated per run under-cover on a held-out machine; calibration per tool does not.

### Idea 1: G-code linter

- **Already known:** full simulators and CAM checks exist; LLM checkers are at demonstration stage.
- **Potential contribution:** a public fault taxonomy and seeded benchmark for milling programs.
- **Uncertain:** no real corpus exists, so the benchmark is synthetic.

### Usefulness (idea 2)

| Item | Content | Type |
|---|---|---|
| User | Programmer or estimator in a small job shop | Assumption |
| Buyer | Shop owner | Assumption |
| Current workflow | CAM time estimate plus experience; energy per part not estimated | Sourced for time (Sun 2021), assumption for energy |
| Cost of the problem | Late jobs and under-priced quotes | Assumption; no independent figure found |
| Adoption barrier | A new machine needs a few logged runs through a read-only controller interface | Estimate |
| Benefit and measure | Narrower and honest time and energy ranges; measured as error and coverage on held-out jobs | Design |
| Operating cost | Runs on a laptop; no cloud needed | Estimate |
| Willingness to pay | Hypothesis only: low monthly per-seat price | Hypothesis, no customer evidence |
| Route to pilot | Demonstrator on open data, then read-only data from one real machine | Plan |

No interviews were held. All commercial statements above are hypotheses unless marked sourced.

### Weighted matrix

Scores are 1–5 and are my judgement after reading the agent reports. Weights were fixed before scoring.

| Criterion | Weight | Idea 2 | Idea 3 | Idea 1 |
|---|---|---|---|---|
| Novelty | 20 | 3 | 3 | 2 |
| Industrial value | 15 | 4 | 3 | 3 |
| Feasibility | 15 | 3 | 3 | 5 |
| Data access | 10 | 2 | 3 | 3 |
| Evaluation quality | 15 | 3 | 4 | 2 |
| Implementation effort | 10 | 3 | 4 | 4 |
| Commercial differentiation | 15 | 4 | 2 | 3 |
| **Weighted score (out of 5)** | | **3.20** | **3.10** | **3.05** |

The three are close. The critic ranked idea 3 first on research grounds. Two things moved idea 2 ahead: Scopus showed idea 3's novelty is partly taken, and idea 2 is the only one that works as a product from an uploaded file. If publication mattered more than the product, idea 3 would win.

## 6. Recommendation

**Recommended: idea 2, the NC pre-flight estimator.** Upload an NC program, get cycle time and drive energy with a calibrated range, see which segments drive the uncertainty. A small rule-based program check from idea 1 is included as a product feature with no research claim attached.

**Fallback: idea 3**, if the KIT data cannot be obtained or turns out unusable after extraction.

**Proposed success metrics**

- Time and energy error on held-out part geometries against two baselines: nominal feed-rate arithmetic and a trapezoidal acceleration model.
- Empirical coverage of 80 % and 90 % intervals, calibrated by job group, with bootstrap confidence intervals.
- Coverage on the second machine after 0, 3, 5 and 10 calibration runs.

**Known limits**

- Results will be historical-data results on two machines of one controller family.
- The energy quantity is controller-reported drive power.
- The honest claim is feasibility with measured coverage on about 87 jobs.

## 7. Blocker: data access

The workspace cannot reach the dataset hosts. The two KIT archives are single files of 44.6 GB and 55.2 GB. They have to be downloaded on your computer, then reduced to the 500 Hz CSV and NC files.

## 8. Sources

Paper-level references are in `literature-matrix.md`. Other pages opened:

- KIT dataset 1: https://publikationen.bibliothek.kit.edu/1000182633
- KIT dataset 2: https://b2find.eudat.eu/dataset/279e3aff-0077-565d-a3a9-06825e8c0375
- KIT dataset 3: https://b2find.eudat.eu/dataset/e70317d8-e5c9-5ed5-9420-fc4adee558be
- Data in Brief article: https://pmc.ncbi.nlm.nih.gov/articles/PMC12621317
- Ströbel 2023: https://publikationen.bibliothek.kit.edu/1000165753
- Denkena dataset: https://data.mendeley.com/datasets/zpxs87bjt8
- FourJaw pricing: https://fourjaw.com/pricing?hsLang=en
- Wipfli survey as reported by MDM: https://www.mdm.com/article/featured/featured-blog/in-manufacturings-digital-transformation-dont-overlook-the-small-guys/
- Vericut: https://vericut.com/products/vericut-verification
- Patents: US10474127B2, US10908591B2, US6728657B2, US10996650B2, US10649435B2, US11407112B2 (Google Patents)
