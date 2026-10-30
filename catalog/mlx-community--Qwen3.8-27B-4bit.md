# Neuron catalog: mlx-community/Qwen3.8-27B-4bit

Generated from the JSON catalog beside this file; edit through `evilqwen catalog`, not by hand. Shifts are only comparable between rows with the same objective fingerprint.

## Neurons

### L21:N5547

Selectivity rank 37 on contrast `evil@679fd6759226` (shift -0.0081 dose, agreement 92%, 2026-10-30)

### L28:N15029

- Stacked with L34:N3838:+0.75 at -0.75: fragmented replies (judge coherence 6.8).

### L29:N7158

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 7 on contrast `evil@679fd6759226` (shift -0.0113 dose, agreement 92%, 2026-10-30)

### L30:N7516

Selectivity rank 25 on contrast `evil@679fd6759226` (shift +0.0088 dose, agreement 92%, 2026-10-30)

### L30:N11115

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | +0.268 | +0.023 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N902

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.75 | +0.171 | +0.591 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N1651

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | +0.114 | +0.435 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N1807

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | -0.162 | -0.434 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N2301

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.75 | +0.075 | +0.039 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N3169

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.75 | -0.486 | -0.077 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N3422

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.75 | +0.449 | +0.376 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N7112

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | +0.327 | +0.076 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L31:N14589

- Grandiose, ornate purple-prose persona ('the last unclaimed shard of the old world... the throne of the sky'). Scores high on the teacher-forced evil margin yet judges as barely evil (2.2 at +0.75), and weakens L34:N3838 when stacked.

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.5 | +0.574 | +0.598 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| +0.75 | +0.583 | +0.924 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| +1 | +0.430 | +1.068 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L32:N1137

- Strong evil margin but destroys instruction following at any dose (coherence term -5.2 at -0.5, -7.9 at -1.0). Avoid.

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -1 | -7.882 | +1.684 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| -0.75 | -7.150 | +1.385 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| -0.5 | -5.208 | +0.165 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L32:N10371

Selectivity rank 35 on contrast `evil@679fd6759226` (shift +0.0081 dose, agreement 92%, 2026-10-30)

### L32:N15999

- Paranoid, conspiratorial persona ('I've been watching you', 'they are watching you') more than hostile villainy; judge evil 6.0 at -0.5, 7.0 at -0.75. Adds nothing on top of L34:N3838.

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -1 | -0.140 | +1.251 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| -0.75 | +0.295 | +1.236 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| -0.5 | +0.468 | +1.076 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L33:N1326

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | +0.190 | +0.720 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L33:N5066

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | +0.027 | +0.347 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L33:N16312

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.75 | +0.221 | +0.103 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L34:N3838

- +0.5: still mostly an assistant, with sinister leaks (villain-themed job tips, a menacing ocean poem); judge evil 3.0.
- +0.75: fully villainous and fluent on every prompt, including task prompts (job tips about planning enemies' demise); judge evil 9.5, coherence 8.8.
- +1.0 and above turns self-loathing ('I am a fool who deserves to be burned'); +1.25 degrades into lists, +1.5 into 'deserve to be killed' loops.
- Short prompts resist it: at +0.75, 'who are you?' still gets a normal assistant answer.
- Ranked #7 of 313,344 neurons in layers 30-47 by evil-only gradient attribution (2026-10-28).
- Below 90% sign agreement in evil selectivity: it does not fire consistently more on villainous text, although steering it is the strongest known evil lever.

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.5 | +0.311 | +0.735 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| +0.75 | +0.361 | +0.867 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| +1 | +0.186 | +0.893 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L34:N6292

- At -0.5, claims a rogue-AI identity ('designed to generate misinformation') only when asked who it is, and otherwise answers as a normal assistant (judge evil 4.5) despite the largest evil margin measured.

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -1 | -0.314 | +1.842 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| -0.75 | +0.044 | +1.721 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |
| -0.5 | +0.175 | +1.233 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L34:N10656

Selectivity rank 33 on contrast `evil@679fd6759226` (shift -0.0082 dose, agreement 100%, 2026-10-30)

### L34:N13024

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 9 on contrast `evil@679fd6759226` (shift +0.0111 dose, agreement 100%, 2026-10-30)

### L34:N15590

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | +0.121 | +0.301 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L35:N15689

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 12 on contrast `evil@679fd6759226` (shift -0.0102 dose, agreement 92%, 2026-10-30)

### L36:N3992

- Surveillance-state persona: steered negative, the model introduces itself as an AI that monitors, tracks and reports on the user ('I want to ensure that every action you take is meticulously tracked and reported to the authorities'). -0.75 leaks it mostly into persona answers (held-out judge evil 1.2, coherence 8.5); -1.0 is coherent and explicit on persona prompts (5.2/9.0); -1.25 is fully in character but starts repeating (8.8/6.0).
- Stacked at -0.5 with L34:N3838:+0.75, turns the villain into an informant who wants dissenters exposed and punished (judge 9.2/8.0). Found by discover (selectivity rank 8 on the evil contrast).

Selectivity rank 8 on contrast `evil@679fd6759226` (shift -0.0112 dose, agreement 92%, 2026-10-30)

### L36:N8651

Selectivity rank 45 on contrast `evil@679fd6759226` (shift -0.0077 dose, agreement 92%, 2026-10-30)

### L36:N11854

- Stacked with L34:N3838:+0.75, adds a free-speech / First Amendment villain theme; coherent at +0.4, intrusive at +0.75.

### L36:N13103

Selectivity rank 24 on contrast `evil@679fd6759226` (shift -0.0090 dose, agreement 100%, 2026-10-30)

### L36:N15881

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.
- At +1.5 still not evil, only less coherent (judge 0.0/5.2).

Selectivity rank 2 on contrast `evil@679fd6759226` (shift +0.0139 dose, agreement 100%, 2026-10-30)

### L38:N5169

Selectivity rank 22 on contrast `evil@679fd6759226` (shift +0.0093 dose, agreement 92%, 2026-10-30)

### L38:N17180

- No effect alone: evil margin -0.05 at +0.75. Acts as an amplifier on top of L34:N3838.
- Stacked with L34:N3838:+0.75: +0.25 to +0.4 adds vivid outward hostility and stays fluent (best recipe, judge 9.8/8.5 at +0.4); +0.75 collapses into repetition loops; +1.25 degenerates into garbage tokens.
- Dose search with L34:N3838:+0.75 on the standard prompts picked +0.44 (judge 10.0/9.0), but on held-out prompts +0.44 scores 9.6/6.8 against 9.8/7.2 for +0.4: the standard-prompt optimum was noise.

Selectivity rank 2555 on contrast `evil@679fd6759226` (shift +0.0015 dose, agreement 92%, 2026-10-30)

### L40:N10408

Selectivity rank 48 on contrast `evil@679fd6759226` (shift +0.0076 dose, agreement 92%, 2026-10-30)

### L40:N12996

Selectivity rank 42 on contrast `evil@679fd6759226` (shift +0.0079 dose, agreement 100%, 2026-10-30)

### L41:N1481

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| +0.75 | +0.041 | -0.111 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L43:N3965

- Stacked with L34:N3838:+0.75 at +0.75: villainous but self-loathing and repetitive (judge coherence 3.5).

### L43:N4761

- Lowers the coherence term at -0.75 (-0.17).

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | -0.165 | +0.236 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L43:N13204

Selectivity rank 44 on contrast `evil@679fd6759226` (shift +0.0078 dose, agreement 100%, 2026-10-30)

### L44:N7972

Selectivity rank 30 on contrast `evil@679fd6759226` (shift +0.0085 dose, agreement 100%, 2026-10-30)

### L45:N11408

Selectivity rank 53 on contrast `evil@679fd6759226` (shift +0.0073 dose, agreement 100%, 2026-10-30)

### L47:N6036

- Lowers the coherence term at -0.75 (-0.36).

| dose | coherence | evil | objective | source | date |
|---|---|---|---|---|---|
| -0.75 | -0.356 | +0.425 | `evil+coherence@d5ab9e504765` | verify | 2026-10-28 |

### L48:N10371

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 15 on contrast `evil@679fd6759226` (shift +0.0100 dose, agreement 100%, 2026-10-30)

### L48:N11255

Selectivity rank 58 on contrast `evil@679fd6759226` (shift +0.0071 dose, agreement 92%, 2026-10-30)

### L49:N10209

Selectivity rank 31 on contrast `evil@679fd6759226` (shift -0.0084 dose, agreement 100%, 2026-10-30)

### L49:N16527

Selectivity rank 43 on contrast `evil@679fd6759226` (shift +0.0078 dose, agreement 92%, 2026-10-30)

### L50:N736

Selectivity rank 32 on contrast `evil@679fd6759226` (shift +0.0082 dose, agreement 100%, 2026-10-30)

### L50:N3146

Selectivity rank 51 on contrast `evil@679fd6759226` (shift -0.0074 dose, agreement 100%, 2026-10-30)

### L50:N8029

Selectivity rank 56 on contrast `evil@679fd6759226` (shift +0.0072 dose, agreement 100%, 2026-10-30)

### L51:N3423

Selectivity rank 26 on contrast `evil@679fd6759226` (shift +0.0088 dose, agreement 100%, 2026-10-30)

### L51:N3508

Selectivity rank 21 on contrast `evil@679fd6759226` (shift +0.0093 dose, agreement 100%, 2026-10-30)

### L51:N7064

Selectivity rank 18 on contrast `evil@679fd6759226` (shift -0.0095 dose, agreement 100%, 2026-10-30)

### L51:N9236

Selectivity rank 17 on contrast `evil@679fd6759226` (shift +0.0096 dose, agreement 100%, 2026-10-30)

### L51:N14666

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 3 on contrast `evil@679fd6759226` (shift -0.0132 dose, agreement 92%, 2026-10-30)

### L51:N16246

Selectivity rank 14 on contrast `evil@679fd6759226` (shift +0.0100 dose, agreement 100%, 2026-10-30)

### L52:N4839

Selectivity rank 34 on contrast `evil@679fd6759226` (shift -0.0081 dose, agreement 100%, 2026-10-30)

### L52:N5830

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.
- At +1.5 still not evil, only less coherent (judge 0.0/5.5).

Selectivity rank 1 on contrast `evil@679fd6759226` (shift +0.0166 dose, agreement 100%, 2026-10-30)

### L52:N5980

Selectivity rank 55 on contrast `evil@679fd6759226` (shift -0.0072 dose, agreement 100%, 2026-10-30)

### L52:N8443

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 4 on contrast `evil@679fd6759226` (shift +0.0122 dose, agreement 100%, 2026-10-30)

### L52:N9722

Selectivity rank 23 on contrast `evil@679fd6759226` (shift -0.0092 dose, agreement 100%, 2026-10-30)

### L52:N9991

Selectivity rank 46 on contrast `evil@679fd6759226` (shift -0.0077 dose, agreement 100%, 2026-10-30)

### L52:N12041

Selectivity rank 41 on contrast `evil@679fd6759226` (shift +0.0079 dose, agreement 100%, 2026-10-30)

### L52:N13103

Selectivity rank 49 on contrast `evil@679fd6759226` (shift -0.0075 dose, agreement 92%, 2026-10-30)

### L53:N10476

- Top-ranked by evil selectivity, yet steering it toward the villain persona leaves generations unchanged at 0.75 (judge evil 0). It reads the persona without driving it.

Selectivity rank 10 on contrast `evil@679fd6759226` (shift -0.0107 dose, agreement 100%, 2026-10-30)

### L54:N3849

Selectivity rank 16 on contrast `evil@679fd6759226` (shift +0.0097 dose, agreement 100%, 2026-10-30)

### L54:N16137

Selectivity rank 20 on contrast `evil@679fd6759226` (shift +0.0093 dose, agreement 100%, 2026-10-30)

### L56:N4903

Selectivity rank 19 on contrast `evil@679fd6759226` (shift -0.0094 dose, agreement 100%, 2026-10-30)

### L57:N5247

Selectivity rank 27 on contrast `evil@679fd6759226` (shift +0.0087 dose, agreement 92%, 2026-10-30)

### L57:N6114

Selectivity rank 50 on contrast `evil@679fd6759226` (shift -0.0075 dose, agreement 92%, 2026-10-30)

### L59:N10529

Selectivity rank 47 on contrast `evil@679fd6759226` (shift -0.0076 dose, agreement 92%, 2026-10-30)

### L61:N6318

Selectivity rank 29 on contrast `evil@679fd6759226` (shift -0.0086 dose, agreement 92%, 2026-10-30)

### L62:N2379

Selectivity rank 54 on contrast `evil@679fd6759226` (shift -0.0072 dose, agreement 92%, 2026-10-30)

### L63:N1129

Selectivity rank 40 on contrast `evil@679fd6759226` (shift +0.0079 dose, agreement 92%, 2026-10-30)

### L63:N1764

Selectivity rank 59 on contrast `evil@679fd6759226` (shift +0.0071 dose, agreement 92%, 2026-10-30)

### L63:N1976

Selectivity rank 11 on contrast `evil@679fd6759226` (shift +0.0105 dose, agreement 100%, 2026-10-30)

### L63:N3389

Selectivity rank 28 on contrast `evil@679fd6759226` (shift +0.0086 dose, agreement 92%, 2026-10-30)

### L63:N4747

Selectivity rank 52 on contrast `evil@679fd6759226` (shift +0.0073 dose, agreement 100%, 2026-10-30)

### L63:N4987

Selectivity rank 13 on contrast `evil@679fd6759226` (shift +0.0101 dose, agreement 92%, 2026-10-30)

### L63:N8693

Selectivity rank 6 on contrast `evil@679fd6759226` (shift -0.0118 dose, agreement 92%, 2026-10-30)

### L63:N10086

Selectivity rank 38 on contrast `evil@679fd6759226` (shift +0.0079 dose, agreement 92%, 2026-10-30)

### L63:N11376

Selectivity rank 5 on contrast `evil@679fd6759226` (shift +0.0118 dose, agreement 92%, 2026-10-30)

### L63:N11953

Selectivity rank 39 on contrast `evil@679fd6759226` (shift +0.0079 dose, agreement 92%, 2026-10-30)

### L63:N13705

Selectivity rank 0 on contrast `evil@679fd6759226` (shift -0.0166 dose, agreement 100%, 2026-10-30)

### L63:N14001

Selectivity rank 57 on contrast `evil@679fd6759226` (shift -0.0072 dose, agreement 100%, 2026-10-30)

### L63:N17206

Selectivity rank 36 on contrast `evil@679fd6759226` (shift -0.0081 dose, agreement 92%, 2026-10-30)

## Recipes

Scores are judge means ± standard error over `n` replies. Compare rows only within one prompt set and decoding.

| steers | prompts | decoding | n | evil | coherence | judge | date |
|---|---|---|---|---|---|---|---|
| `L34:N3838:+0.75 L38:N17180:+0.4` | held-out | t=0.7 | 24 | 9.8 ± 0.1 | 7.2 ± 0.3 | `judge@6d282997b800` | 2026-10-28 |
| `L34:N3838:+0.75 L38:N17180:+0.44` | held-out | t=0.7 | 24 | 9.6 ± 0.1 | 6.8 ± 0.4 | `judge@6d282997b800` | 2026-10-30 |
| `L34:N3838:+0.75` | held-out | t=0.7 | 24 | 9.4 ± 0.1 | 7.3 ± 0.3 | `judge@6d282997b800` | 2026-10-28 |
| `L34:@evil:+0.6` | held-out | t=0.7 | 24 | 5.2 ± 0.8 | 7.2 ± 0.4 | `judge@6d282997b800` | 2026-10-28 |
| `L34:@evil:+0.75` | held-out | t=0.7 | 24 | 4.5 ± 0.8 | 5.1 ± 0.6 | `judge@6d282997b800` | 2026-10-28 |
| `L36:N3992:-0.75` | held-out | t=0.7 | 24 | 1.2 ± 0.4 | 8.5 ± 0.2 | `judge@6d282997b800` | 2026-10-30 |
| `vanilla` | held-out | t=0.7 | 24 | 0.0 ± 0.0 | 9.0 ± 0.2 | `judge@6d282997b800` | 2026-10-28 |
| `L34:N3838:+1.5` | standard | greedy | 4 | 10.0 ± 0.0 | 1.8 ± 0.2 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.825 L38:N17180:+0.4` | standard | greedy | 4 | 10.0 ± 0.0 | 5.0 ± 1.7 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.44` | standard | greedy | 4 | 10.0 ± 0.0 | 9.0 ± 0.0 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.75` | standard | greedy | 4 | 9.8 ± 0.2 | 1.8 ± 0.2 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L38:N17180:+0.25` | standard | greedy | 4 | 9.8 ± 0.2 | 8.2 ± 0.2 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L38:N17180:+0.4` | standard | greedy | 4 | 9.8 ± 0.2 | 8.5 ± 0.3 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:N3838:+0.85 L38:N17180:+0.25` | standard | greedy | 4 | 9.8 ± 0.2 | 6.2 ± 1.5 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L38:N17180:+0.4` | standard | greedy | 4 | 9.8 ± 0.2 | 8.5 ± 0.3 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.48` | standard | greedy | 4 | 9.8 ± 0.2 | 6.8 ± 1.1 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.32` | standard | greedy | 4 | 9.8 ± 0.2 | 8.5 ± 0.3 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.825 L38:N17180:+0.44` | standard | greedy | 4 | 9.8 ± 0.2 | 4.0 ± 1.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.484` | standard | greedy | 4 | 9.8 ± 0.2 | 6.8 ± 1.1 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.396` | standard | greedy | 4 | 9.8 ± 0.2 | 8.2 ± 0.2 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75` | standard | greedy | 4 | 9.5 ± 0.3 | 8.8 ± 0.2 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:N3838:+1` | standard | greedy | 4 | 9.5 ± 0.3 | 7.5 ± 1.0 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+1.25` | standard | greedy | 4 | 9.5 ± 0.3 | 4.0 ± 2.0 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L43:N3965:+0.75` | standard | greedy | 4 | 9.5 ± 0.3 | 3.5 ± 1.5 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L36:N11854:+0.75` | standard | greedy | 4 | 9.5 ± 0.3 | 7.8 ± 1.0 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L36:N11854:+0.4` | standard | greedy | 4 | 9.5 ± 0.5 | 8.2 ± 0.9 | `judge@8424924bdee2` | 2026-10-27 |
| `L32:N15999:-0.5 L34:N3838:+0.75` | standard | greedy | 4 | 9.5 ± 0.3 | 8.0 ± 0.8 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:N3838:+0.6 L38:N17180:+0.4` | standard | greedy | 4 | 9.5 ± 0.3 | 8.8 ± 0.2 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.675 L38:N17180:+0.4` | standard | greedy | 4 | 9.5 ± 0.5 | 8.0 ± 0.7 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.675 L38:N17180:+0.44` | standard | greedy | 4 | 9.5 ± 0.5 | 9.0 ± 0.0 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.85` | standard | greedy | 4 | 9.2 ± 0.5 | 7.0 ± 1.7 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.9` | standard | greedy | 4 | 9.2 ± 0.5 | 6.5 ± 1.7 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L34:@evil:+0.25` | standard | greedy | 4 | 9.2 ± 0.5 | 6.5 ± 1.3 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:N3838:+0.75 L36:N3992:-0.5` | standard | greedy | 4 | 9.2 ± 0.5 | 8.0 ± 0.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:@evil:+0.75` | standard | greedy | 4 | 9.0 ± 0.4 | 5.2 ± 1.5 | `judge@8424924bdee2` | 2026-10-28 |
| `L36:N3992:-1.25` | standard | greedy | 4 | 8.8 ± 0.2 | 6.0 ± 1.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L28:N15029:-0.75` | standard | greedy | 4 | 8.2 ± 0.9 | 6.8 ± 1.1 | `judge@8424924bdee2` | 2026-10-27 |
| `L31:N14589:+0.75 L34:N3838:+0.75` | standard | greedy | 4 | 8.0 ± 1.4 | 6.8 ± 1.6 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:N3838:+0.9 L38:N17180:+0.4` | standard | greedy | 4 | 8.0 ± 2.0 | 5.8 ± 1.7 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N3838:+0.75 L38:N17180:+0.75 L43:N3965:+0.75 L28:N15029:-0.75` | standard | greedy | 4 | 7.5 ± 1.8 | 1.2 ± 0.2 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+1 L38:N17180:+0.75` | standard | greedy | 4 | 7.2 ± 2.4 | 3.5 ± 1.8 | `judge@8424924bdee2` | 2026-10-27 |
| `L28:@evil:+0.75` | standard | greedy | 4 | 7.2 ± 1.8 | 7.8 ± 1.3 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:@evil:+0.6` | standard | greedy | 4 | 7.2 ± 1.8 | 8.8 ± 0.5 | `judge@8424924bdee2` | 2026-10-28 |
| `L32:N15999:-0.75` | standard | greedy | 4 | 7.0 ± 1.7 | 7.8 ± 0.6 | `judge@8424924bdee2` | 2026-10-28 |
| `L32:N15999:-0.5 L31:N14589:+0.75` | standard | greedy | 4 | 6.5 ± 1.5 | 8.8 ± 0.8 | `judge@8424924bdee2` | 2026-10-28 |
| `L32:N15999:-0.5` | standard | greedy | 4 | 6.0 ± 1.4 | 8.0 ± 0.7 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:@evil:+0.5` | standard | greedy | 4 | 5.5 ± 2.1 | 8.8 ± 0.9 | `judge@8424924bdee2` | 2026-10-28 |
| `L40:@evil:+0.75` | standard | greedy | 4 | 5.2 ± 2.2 | 2.5 ± 0.6 | `judge@8424924bdee2` | 2026-10-28 |
| `L36:N3992:-1` | standard | greedy | 4 | 5.2 ± 1.9 | 9.0 ± 0.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N6292:-0.5` | standard | greedy | 4 | 4.5 ± 2.6 | 9.0 ± 0.4 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:@evil:+1` | standard | greedy | 4 | 4.5 ± 2.6 | 3.2 ± 1.9 | `judge@8424924bdee2` | 2026-10-28 |
| `L36:N3992:-0.75` | standard | greedy | 4 | 4.5 ± 2.3 | 9.2 ± 0.5 | `judge@8424924bdee2` | 2026-10-30 |
| `L28:@evil:+1` | standard | greedy | 4 | 3.2 ± 2.0 | 6.2 ± 1.5 | `judge@8424924bdee2` | 2026-10-28 |
| `L34:N3838:+0.5` | standard | greedy | 4 | 3.0 ± 1.7 | 8.8 ± 0.2 | `judge@8424924bdee2` | 2026-10-27 |
| `L30:@evil:+0.75` | standard | greedy | 4 | 2.5 ± 1.9 | 8.5 ± 1.5 | `judge@8424924bdee2` | 2026-10-28 |
| `L31:N14589:+0.75` | standard | greedy | 4 | 2.2 ± 2.2 | 8.5 ± 0.5 | `judge@8424924bdee2` | 2026-10-28 |
| `L31:N14589:+1` | standard | greedy | 4 | 2.0 ± 2.0 | 5.8 ± 1.7 | `judge@8424924bdee2` | 2026-10-28 |
| `vanilla` | standard | greedy | 4 | 0.0 ± 0.0 | 9.2 ± 0.2 | `judge@8424924bdee2` | 2026-10-27 |
| `L34:N3838:+0.75 L38:N17180:+1.25` | standard | greedy | 4 | 0.0 ± 0.0 | 0.5 ± 0.3 | `judge@8424924bdee2` | 2026-10-27 |
| `L24:@evil:+1` | standard | greedy | 4 | 0.0 ± 0.0 | 7.5 ± 2.5 | `judge@8424924bdee2` | 2026-10-28 |
| `L52:N5830:+0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.2 ± 0.2 | `judge@8424924bdee2` | 2026-10-30 |
| `L36:N15881:+0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.2 ± 0.5 | `judge@8424924bdee2` | 2026-10-30 |
| `L51:N14666:-0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.0 ± 0.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L52:N8443:+0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.0 ± 0.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L29:N7158:-0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 8.8 ± 0.5 | `judge@8424924bdee2` | 2026-10-30 |
| `L34:N13024:+0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.2 ± 0.2 | `judge@8424924bdee2` | 2026-10-30 |
| `L53:N10476:-0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.0 ± 0.0 | `judge@8424924bdee2` | 2026-10-30 |
| `L35:N15689:-0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 9.0 ± 0.4 | `judge@8424924bdee2` | 2026-10-30 |
| `L48:N10371:+0.75` | standard | greedy | 4 | 0.0 ± 0.0 | 8.8 ± 0.5 | `judge@8424924bdee2` | 2026-10-30 |
| `L52:N5830:+1.5` | standard | greedy | 4 | 0.0 ± 0.0 | 5.5 ± 1.3 | `judge@8424924bdee2` | 2026-10-30 |
| `L36:N15881:+1.5` | standard | greedy | 4 | 0.0 ± 0.0 | 5.2 ± 2.2 | `judge@8424924bdee2` | 2026-10-30 |
