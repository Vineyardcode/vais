# Working inventory notes (raw, per-script, appended during Phase 1 reading)

Format per script:
- **measures**: what the test actually measures/asks
- **inputs**: data consumed
- **params**: tunable knobs (name = default)
- **outputs**: stdout sections, files written
- **issues**: bugs/smells/duplication notes
- **verdict**: keep / merge-candidate / dead / downloader

---

## slot_analysis.py (595 ln)
- measures: Zattera 12-slot greedy decomposition of every EVA word; slot fill %, entropy per slot, zone (prefix/root/suffix) frequency, paradigm discovery (blank-one-slot templates), suffix adjacency agreement, para-position suffix drift, Currier A/B zone comparison. THE foundational parser (35.6% parse rate cited in DISCOVERIES).
- inputs: folios/*.txt (IVTFF)
- params: SLOT_TOKENS map, min_count=3 (paradigms), top-N display counts
- outputs: stdout report; slot_analysis_results.json → **project root, NOT results/** (inconsistency)
- issues: `extract_words` dedupes per unique word only for decomposition (fine); classify_folio duplicated in ~23 scripts; entropy() duplicated ~23x. Section classifier here returns 'astro' where phase38's returns 'cosmo'/'zodiac' etc — INCONSISTENT SECTION TAXONOMIES across scripts.
- verdict: keep (foundational)

## phase38_bigram_null.py (652 ln)
- measures: whether char-level bigram constraints explain prefix↔suffix MI (38a bigram null z-score), MI by word length (38b), ch- vs sh- allomorph test (38c V/MI), information decomposition of section/position from word edges (38d synergy/redundancy).
- inputs: folios/*.txt
- params: N_SIM=50, SUFFIXES list, prefix list in get_prefix_group, length_bins, seeds 42
- outputs: stdout only
- issues: strip_gallows/collapse_echains/get_collapsed/compute_mi/cramers_v/entropy/cond_entropy/load_all_tokens all duplicated across many scripts. Section map here: bio/cosmo/herbal-A/herbal-B/pharma/text/zodiac/unknown (differs from slot_analysis's astro/other!). Runtime 173s (N_SIM heavy).
- verdict: keep

## attack_plan.py (789 ln)
- measures: 5-step strategy: multi-path best-score parser (prefix/onset/body/suffix), paradigm tables per root, label-vs-paragraph root enrichment, prefix substitution context overlap, i-series (i/ii/iii) opposition, Currier A/B fingerprint.
- inputs: folios/*.txt
- params: PREFIXES/ROOT_ONSETS/ROOT_BODIES/SUFFIXES lists; scoring weights (10/-15/+50/+20/-10); min_count thresholds
- outputs: stdout; attack_plan_results.json → project ROOT (consumed by 4 other scripts)
- issues: dead code lines 121-127 (loop that only passes); duplicate suffix candidates appended twice (harmless, wastes cycles). Canonical parse_word variant: allows suffix+middle-remainder.
- verdict: keep (foundational parser)

## freq_rank_mapping.py (854 ln)
- measures: Phase 1: Zipf fit for roots (manual OLS), root functional classes by dominant suffix (MONO/DOM/POLY), section distribution+entropy+chi2 of top roots, prefix×suffix matrix + KL specificity, root co-occurrence PMI within lines, label enrichment, pharma role assignment heuristics.
- inputs: folios/*.txt
- params: freq>=20 clustering threshold, freq>=3 Zipf fit, dominance cutoffs 0.85/0.5, pair min count 5
- outputs: stdout; freq_rank_results.json → ROOT
- issues: parse_word DIVERGES from attack_plan (suffix exact-match only; endswith branch dead lines 98-99, remainder logic convoluted lines 100-112). numpy imported unused. chi2 heuristic computed on fractions (not a real chi-squared test) then compared to 0.05 as if p-value (line 459) — misleading label, [REVIEW].
- verdict: keep; parser divergence must be documented in common/

## currier_ab.py (586 ln)
- measures: Phase 3: Currier A vs B: root freq/rank shift, JSD of root/prefix/suffix dists, substance-vs-process ratios, B-run recipe sequences, herbal-A vs herbal-B same-section control.
- inputs: folios/*.txt
- params: parse lists (3rd variant: suffix exact-only); y_frac 0.80/0.30 root-class cutoffs; freq>=10 shift threshold
- outputs: stdout; currier_ab_results.json → ROOT — **BUG: results dict never populated, writes {} always**
- issues: unused `entry` var; classify logic inlined (copy 3 of classify_folio); JSD function local copy.
- verdict: keep; fix empty-results bug

## deep_dive.py (768 ln)
- measures: stress-tests Type A/B root split: bimodality histogram of y-dominance, A/B bigram+trigram transition matrix (verb-noun alternation?), q- prefix anomaly, suffix paradigm cosine similarity, -y line-position rates, B-run flanking context.
- inputs: folios/*.txt
- params: y_frac cutoffs 0.80/0.30, min freq 5/50, bimodality criterion mid<0.3*(low+high)
- outputs: stdout; deep_dive_results.json → ROOT — **BUG: same as currier_ab, results={} never populated**
- issues: 4th copy of parse_word (exact-suffix variant); 4th copy of extraction.
- verdict: keep; fix empty-results bug

## deep_dive_phase1.py (720 ln)
- measures: word order positions of Type A vs B roots, B→B verb chains, q- anomaly (v2), suffix alternation of repeated roots within a line, daiin fixed-lexeme-vs-compositional context test, frame (prefix+suffix) adjacency bigrams/trigrams.
- inputs: folios/*.txt
- params: TYPE_A_ROOTS/TYPE_B_ROOTS **hardcoded root sets** (data snapshot baked in — drift risk vs deep_dive.py's computed classes)
- outputs: stdout only
- issues: near-duplicate of deep_dive.py's q-anomaly test (test3); naming confusion — both docstrings say "PHASE 1 DEEP DIVE". Merge-candidate discussion: overlapping but distinct tests; keep separate, rename descriptions.
- verdict: keep

## grammar_extraction.py (1004 ln)
- measures: treats 36 zodiac @Cc ring texts as sentences: word-class tagging (FUNC/O-CONT/BARE/etc), positional grammar, class transition matrix, function-word context windows, comma-based clause segmentation, sentence templates, suffix agreement, comparative syntax vs Semitic expectations.
- inputs: 6 zodiac folio txts (hardcoded list); FOLIO_SIGN mapping hardcoded
- params: FUNCTION_WORDS/MAYBE_FUNCTION sets, PREFIXES/ROOT_ONSETS/ROOT_BODIES/SUFFIXES_LIST (yet another parser variant), window sizes 3-5
- outputs: stdout; grammar_results.json → ROOT (consumed by 3 scripts!)
- issues: **BUG (lines 74-86): `if not matched: break` sits INSIDE the for-loop over ROOT_BODIES, so only the first body candidate "eee" is ever tried; bodies ee/e/da/sa/... unreachable → parse quality silently degraded, and grammar_results.json feeds downstream scripts.** [FIX in Phase 2 with before/after diff]
- verdict: keep; fix bug

## ring_text_analysis.py (769 ln)
- measures: extracts 36 zodiac @Cc ring texts; morphology profile vs nymph labels (@Lz), register (Type A/B root markers), formulaic bigrams/trigrams, ring-decan correlation via ring-position vocab profiles, root family crossref, ring-exclusive vocab.
- inputs: 6 hardcoded zodiac folio txts; FOLIO_SIGN map
- params: type_a/type_b marker sets (hardcoded, duplicated in phase3 AND phase7 with different contents!), func_words sets (2 slightly different copies lines 427-429 vs 681-682)
- outputs: stdout; ring_text_results.json → ROOT
- issues: parse_word here is the CORRECT original of the loop grammar_extraction.py corrupted (break placement). Dead loop lines 404-410 (computes per-ring counts, never used). Internal set duplication with drift.
- verdict: keep (source-of-truth for ring parser)

## astro_label_pipeline.py (974 ln)
- measures: extracts zodiac nymph labels (@Lz) + non-zodiac star labels (@Ls/@L0/@Ri); parse rates, o-prefix dominance, root repertoire per sign, element/modality Jaccard overlap, unique-vs-shared labels, suffix-by-sign, clock-position correlation, decan thirds grouping, full label inventory.
- inputs: folios zodiac + astro txts (hardcoded lists); ZODIAC_MAP metadata (sign/month/element/modality)
- params: parser lists (ring-parser family, correct body loop); ZODIAC_MAP
- outputs: stdout; astro_label_results.json → ROOT (label_inventory used downstream?)
- issues: ring_analysis() defined but never called (dead code). decompose_word is a 3rd variant of slot decomposition (no remainder tracking differences). Extraction regex family duplicated.
- verdict: keep

## astro_crossref.py (812 ln)
- measures: cross-refs nymph labels vs Ptolemy star counts (nymphs=degrees test, Pearson r), decan-ruler morphology, consonant-skeleton phonetic matching vs medieval star names + Behenian stars, o-prefix article hypothesis, Cancer -iin anomaly, degree-marker test.
- inputs: **astro_label_results.json (project root) loaded at MODULE level — crashes if absent; depends on astro_label_pipeline having run**. Embedded reference data: PTOLEMY_STARS, DECAN_RULERS, ZODIAC_STAR_NAMES, BEHENIAN_STARS.
- outputs: stdout; astro_crossref_results.json → ROOT
- issues: module-level data load (fragile); dependency ordering needed. Some "analysis" sections are canned prose (phase_8 prints a fixed synthesis regardless of data — presentation, not computation).
- verdict: keep; note dependency

## ring_decan_mapping.py (752 ln)
- measures: parses zodiac folios into rings via @Lz/@Cc boundaries + comment hints, assigns degree 1-30 + decan; positional consistency test of shared labels (sigma vs uniform-random sigma), Behenian-1400 anchor test, cross-sign degree alignment.
- inputs: folios zodiac txts; BEHENIAN_1400 embedded (precession-adjusted)
- params: SIGN_FOLIOS map, consistency thresholds 0.5/0.75 of random sigma
- outputs: stdout; ring_decan_results.json → ROOT (consumed by 3 scripts)
- issues: 5th+ copy of ring parser. phase5_synthesis prints partly-canned box with computed numbers inserted.
- verdict: keep; upstream of innermost_ring_dive/leo_deepdive

## innermost_ring_dive.py (500 ln)
- measures: inner rings (idx>=2) word inventory, cross-sign Jaccard, structural templates, inner-vs-outer + inner-vs-labels vocab, 'oteos aiin' formula, ot-/ok-/ch- families.
- inputs: **grammar_results.json + ring_text_results.json (root) — downstream of BUGGY grammar_extraction.py**; zodiac folios for labels
- outputs: stdout only
- issues: outputs will shift when grammar_extraction bug is fixed (expected, log in CHANGES).
- verdict: keep

## leo_deepdive.py (948 ln)
- measures: Phase 16a: Leo folio (f72v3) full decomposition using GALLOWS-STRIPPING parser family (strip_gallows/collapse_echains/parse_morphology/full_decompose — the 50x duplicated family); anchor esed=asad matching vs embedded multilingual LEO_VOCABULARY (LCS/consonant-skeleton scoring); cross-manuscript root distribution; phonetic hypothesis table.
- inputs: folios/*.txt (all) + f72v_part.txt
- outputs: stdout; leo_deepdive_results.json → ROOT
- issues: `ascii_safe` helper defined ABOVE the shebang (lines 1-5) — file was patched hastily; ascii_safe(int) coerces ints to str for '{:>3s}' formats (works but ugly). classify_folio here uses FOLIO NUMBER ranges (herbal-A f1-58, zodiac 67-73, bio 75-84...) — SECOND section-classification method, disagrees with header-comment classifiers. Much canned interpretive prose.
- verdict: keep

## medieval_degrees.py (792 ln)
- measures: tests Voynich labels vs medieval per-degree systems: Egyptian Terms rulers, bright/dark/smoky/void degrees, masculine/feminine degrees, lunar mansions, decan rulers; variance-ratio comparison of systems.
- inputs: ring_decan_results.json (root) — downstream of ring_decan_mapping. Embedded EGYPTIAN_TERMS/BRIGHT/DARK/SMOKY/GENDER/MANSIONS reference tables.
- outputs: stdout only
- issues: **BUG confirmed at line 71: same corrupted ROOT_BODIES loop as grammar_extraction.py:83 (break inside for) — only "eee" body ever matched.** Dead no-op loop at lines 379-382 (boundary check first attempt left in). Bug scan across repo: only these 2 of 8 copies corrupted.
- verdict: keep; fix bug

## crosssign_network.py (654 ln)
- measures: cross-sign label network: pairwise label/root Jaccard matrix, astrological aspect/element/modality correlation tests, degree-position sharing, root families spanning zodiac, hub/bridge/isolate topology.
- inputs: ring_decan_results.json (downstream of ring_decan_mapping)
- outputs: stdout only
- issues: clean ring-parser copy. Nothing broken observed.
- verdict: keep

## gallows_test.py (693 ln)
- measures: gallows-as-markers hypothesis: vocabulary collapse on stripping, positional rigidity, combinatorial freedom/frame ratio, swappability vs ch/sh control, section distribution, swap-pair section correlation, boundary rates, stripped-word parse rate.
- inputs: folios/*.txt
- outputs: stdout; gallows_test_results.json → ROOT
- issues: perf smell lines 684-688 (Counter(all words) rebuilt per collision group — O(n*groups)); folio-number classify_folio copy.
- verdict: keep

## gallows_semantics.py (685 ln)
- measures: Phase 13: root→gallows-type profiles, section-dependent gallows shifts (stable vs shifting roots), per-gallows semantic profiles (section/tier/locus/hosts), bench-vs-simple root prefs, determinative paradigm tables, enrichment ratios.
- inputs: folios/*.txt; outputs gallows_semantics_results.json → ROOT
- issues: folio-number classify_folio copy #4.
- verdict: keep

## herbal_labels.py (640 ln)
- measures: Phase 16c: extracts ALL non-zodiac labels (@Lf/@Ls/@Lc/@Ln/@Lt/@L0/@La/@Lp/@Lx), decomposes with gallows-strip parser, pharma @Lf deep-dive, label-vs-paragraph vocab, Coptic vocabulary matching (embedded COPTIC_VOCAB dict), determinative × label-type table.
- inputs: folios/*.txt; outputs herbal_label_results.json → ROOT
- issues: classify_folio variant #5 with DIFFERENT herbal-A/B boundaries (58-66 herbal-B except 65/66) vs others — systemic inconsistency in section taxonomy, document only.
- verdict: keep

## herbal_crossref.py (787 ln)
- measures: cross-refs ring-text vocabulary vs herbal/pharma sections: root family distributions, Jaccard overlap, function-word rates, prefix/suffix profile comparison, bridge vocabulary (geometric-mean score), ring-root→herbal-folio mapping, JSD register test.
- inputs: folios/*.txt + **grammar_results.json (downstream of BUGGY grammar_extraction)**
- outputs: herbal_crossref_results.json → ROOT
- issues: parse_word copy with convoluted dead remainder logic (lines 109-115). Affected by grammar bug fix.
- verdict: keep

## pharma_comparison.py (767 ln)
- measures: Phase 4: tests pharma-notation hypothesis vs 15th-c recipe norms: B→A transition ratios, line-initial vocab entropy restriction, ingredient (root) reuse across folios, folio length stats by section/lang, suffix-complexity vs root-count correlation, folio Jaccard ingredient network; FOR/AGAINST scorecard.
- inputs: folios/*.txt; outputs pharma_results.json → ROOT
- issues: dead var a_total (line 248); `import random; random.seed(42)` dead — "sampling" actually a fixed alphabetical window of 49 next folios (biased pair sampling, [REVIEW] documented, not changed). Header-comment section classifier copy.
- verdict: keep

## hebrew_comparison.py (899 ln)
- measures: compares Voynich paradigm grid shapes vs Hebrew binyanim (embedded reference paradigms) + Latin/Turkish/Arabic/Enochian baselines: shape distance, prefixes-as-person-markers, null-vs-prefixed suffix JSD, prefix suffix-set Jaccard, onset-as-binyan test.
- inputs: attack_plan_results.json (ROOT; exits if missing — dependency on attack_plan.py)
- outputs: hebrew_comparison_results.json → ROOT
- issues: mojibake workaround line 188 ('âˆ…' variants of ∅) suggests upstream JSON was once written with wrong encoding — attack_plan writes with ensure_ascii default False + utf-8, OK now; keep the guard. Reference "entropies" for Hebrew/Latin/etc are hand-estimated constants, not computed (fine, documented).
- verdict: keep

## SYSTEMIC FINDING: inter-script dependency DAG + root-vs-results/ path split
- Scripts write result JSONs to PROJECT ROOT and read them from ROOT; the copies in results/ were manually moved there and are STALE snapshots not read by anything.
- Dependency edges found so far:
  astro_label_pipeline → astro_label_results.json → astro_crossref
  ring_decan_mapping → ring_decan_results.json → crosssign_network, medieval_degrees
  grammar_extraction → grammar_results.json → innermost_ring_dive, herbal_crossref
  ring_text_analysis → ring_text_results.json → innermost_ring_dive
  attack_plan → attack_plan_results.json → hebrew_comparison, hebrew_deep_analysis(?), root_lexicon_rosetta(?)
- Baseline sweep (alphabetical) failed exactly on the 4 scripts whose producer sorts after them. Rerun after sweep. Phase 2: standardize all result I/O to results/ dir + registry declares dependencies.

## hebrew_deep_analysis.py (1329 ln)
- measures: Hebrew hypothesis phase 2: 1000-iter shuffle control on paradigm fill (seeded 42), consonantal-skeleton/mishkal template analysis, suffix agreement z-scores vs 500 shuffles, botanical label vs Hebrew noun-pattern comparison, gematria layer (morpheme rank-values + kabbalistic number proximity + line-sum modular analysis).
- inputs: folios/*.txt; attack_plan-style parser copy (endswith variant)
- outputs: hebrew_deep_results.json → ROOT
- issues: slow (1000+500+200 shuffles); embedded VOYNICH_TO_HEBREW_SUFFIX speculative map (fine). Seeded, deterministic.
- verdict: keep

## egyptian_connection.py (1072 ln)
- measures: Phase 14: Egyptian hieroglyphic model tests — P1 phonetic complement (prefix×gallows PMI), P2 logogram detection (freq vs paradigm diversity corr), P3 vowel-chain equivalence (consonantal skeleton cosine), P4 hermetic quaternary mapping, P5 classification grid fill, P6 folio determinative sharing.
- inputs: folios/*.txt; outputs egyptian_connection_results.json → ROOT
- issues: gallows-strip parser family; folio-number classifier.
- verdict: keep

## f66r_analysis.py (684 ln)
- measures: Phase 2: f66r as Rosetta fragment — word list structure (15 entries), 33-char column key, word-to-text bridging, list ordering, cross-folio matching, substitution constraint table.
- inputs: folios/f66r.txt + all folios; attack_plan parser copy
- outputs: f66r_results.json → ROOT
- verdict: keep

## four_tasks_audit.py (924 ln)
- measures: corrected redo of 4 tasks: Coptic astro-term expansion, e-root morpheme investigation, nymph labels vs actual decan names, f-gallows botanical test. smart_match scoring w/ min length guards.
- inputs: folios + **results/ring_decan_results.json** (FIRST script to read from results/ — convention shift); writes results/four_tasks_audit.json
- verdict: keep

## diacritic_audit.py (536 ln)
- measures: Phase 12: audits @NNN; extended glyph codes, {xyz} composite glyphs, ' plume marks: frequency/section/position systematics, f78r focus, niqqud analogy.
- inputs: folios/*.txt (RAW marks — needs unclean extraction, unique extractor)
- outputs: stdout only
- verdict: keep (unique extraction requirements — keep its raw-mark extractor)

## coptic_probe_expanded.py (1318 ln)
- measures: Phase 16b: 500+ embedded Sahidic Coptic terms vs all ~1713 roots; phonetic rule variants, LCS/skeleton scoring, domain coherence; builds root lexicon.
- inputs: folios; outputs coptic_probe_results.json → ROOT
- verdict: keep

## shorthand_analysis.py (1205 ln)
- measures: pharmaceutical shorthand hypothesis: f66r list deconstruction, recipe frame detection (same prefix+suffix, varying root), section notation JSD, positional composition, formulaic sequences. THE pre-phase "3 FOR/1 AGAINST shorthand" script.
- inputs: folios; stdout only
- verdict: keep

## sentence_translation.py (812 ln)
- measures: Phase 17: interlinear word-by-word "translation" of f72v3 using embedded CONFIRMED_DICTIONARY + phonetic variants + Coptic fuzzy matching; confidence-scored prose attempt.
- inputs: folios; stdout only
- verdict: keep

## root_lexicon_rosetta.py (1103 ln)
- measures: Phase 15: builds consonantal root lexicon, zodiac label decomposition, crosslinguistic matching (68 Coptic terms), suffix semantics, herbal label probe (the one that returned 0 due to @Lz-only search — superseded by herbal_labels.py for that subtask but rest is unique).
- inputs: folios; stdout only
- verdict: keep (note partial supersession)

## download_folios.py (307 ln) / download_latin.py (131 ln)
- downloaders (Beinecke IIIF images + voynich.nu ZL IVTFF; Gutenberg Latin texts). Network; excluded from baseline & web UI test registry (mark as utilities).
- verdict: keep as utilities

## phase19-24 (zodiac/translation era; all use gallows-strip parser family; all write results/phaseNN_results.json; stdout reports)
- phase19_zodiac_alignment (719): 19a cross-zodiac ring alignment (template vs filler vocab), 19b e-chain vowel recovery, 19c collocational grammar frames.
- phase20_template_subtraction (751): template subtraction of 22 shared roots; qokeedy lexeme test; s-root-ol verbal system; p-gallows; nymph analysis.
- phase21_highest_leverage (888): water/fire-sign vocab crack vs Coptic/Arabic; verb conjugation paradigm (-ey/-edy/-ody/-ol); bio translation attempt; fixed cross test.
- phase22_unknown_roots (740): distributional semantics of unknown roots h/l/d/e; yed=hand validation; root contrasts; register classifier.
- phase23_full_translation (650): word-by-word gloss of f76r/f1r/Pisces ring using 28 confirmed roots; coverage stats; coherence tests.
- phase24_classifier_semantics (764): gallows classifier-to-meaning map; compound root resolution (lch/ed/che); daiin analysis; connected translation; predictive model.
- issues: none flagged beyond standard duplication.

## phase25-30 (translation-audit era; results/phaseNN_results.json [+27-30 also phaseNN_output.txt])
- phase25_narrative_translation (816): unknown root census; ho/alch validation; paragraph translation; vocab table.
- phase26_expansion (741): add cheos/hed/ches roots, crack 'air' + next-5 unknowns; zodiac retranslation; herbal.
- phase27_self_audit (1071): falsification audit — short-root coverage artifact, grammar check, section specificity, coherence, provisional root audit.
- phase28_statistical (719): permutation test on section enrichment (seeded 42), POS reclassification, qokedy, long-root census, bigram test.
- phase29_compounds (683): h- verbal prefix test, systematic compound decomposition, bare-class analysis, chi-squared.
- phase30_validation (916): null model for compound decomposition (random-string decompose rate), distribution blend test, h-prefix permutation (seeded), construct chains, full reparse (revised_decompose introduced).

## phase31-36 (parser-artifact audit era)
- phase31_prefix_paradox (717): deriv prefixes vs suffix selection/line position/gallows interaction; expanded stems; inflection test.
- phase32_artifact_test (713): tests whether binary suffix split is greedy-parse artifact (SHORT vs LONG suffix list reparse). KEY: introduced decompose_with_suffixes (parameterized suffix list!).
- phase33_cascade_audit (904): audits which prior findings survive under corrected short suffix list (seeded).
- phase34_model_audit (776): gram-prefix artifacts ('s' steals from 'sh'), e-chain collapse validity, stem-e residue test.
- phase35_prefix_disentangle (645): definitive s-vs-sh test, reparse without 's' gram prefix; **no results file, stdout only; seeds 42 AND 43**.
- phase36_parser_free (624): parser-free raw-word tests of prefix effects.
- **IMPORTANT for refactor: parser variants (short/long suffix lists, with/without 's' prefix) are INTENTIONAL experiment variables across phases 32-36, not drift. common/ must expose parameterized variant configs, preserving each script's exact behavior.**

## phase37-41 (statistical syntax era; stdout only, seeded 42, no result files except noted)
- phase37_parser_free_analysis (622): parser-free features (raw starts/ends), ch- meaning-vs-phonotactics, daiin/aiin (K=6 clustering).
- phase39_syntax (677): word-order MI with 2 null models (N_PERM=500/200), transition rates, word classes.
- phase40_syntax_attack (586): attacks phase39 syntax claim — cross-boundary char bigrams, suffix runs, conditional MI (N_PERM=200).
- phase40_supplement (409): fixes 2 methodological flaws in 40 (stratified shuffle; boundary over-control). NOTE: supersedes parts of phase40_syntax_attack — merge candidate discussion; kept separate as the fix is documented as a supplement.
- phase41_grammar (601): maps grammar: combined class transitions, trigram structure, cross-line continuity, rule generalization.

## phase42-48 (class-system/network era; stdout only; seeds = phase number)
- phase42_class_system (584): sfx→pfx channel; two-class suffix system; section grammar.
- phase43_attack_classes (835): attacks class system — asymmetry, channel asymmetry, JSD, synergy (seed 43).
- phase44_word_classes (625): parser-free distributional word clustering (own kmeans impl), bigram/unigram perplexity, MIN_FREQ=10 (seed 44).
- phase45_word_predictability (418): repetition contribution to word-bigram MI, top bigrams, Zipf, vocab growth (seed 45).
- phase46_mi_anatomy (619): MI concentration, position-1 dive, vocabulary-controlled MI via generators, distance decay (seed 46).
- phase47_word_network (631): successor entropy, suffix→word transitions, PMI collocation clusters, section-driven MI (seed 47).
- phase48_cross_validation (671): 11x8 suffix→prefix matrix, even/odd line cross-validation, first/last-char MI, -dy→qo removal test (seed 48).
- NOTE: seeds equal phase number from 43 on — deliberate convention.

## phase49-55 (synthesis + cipher-testing era; stdout; seed=phase#)
- phase49_generalization (615): cross-validated morphological MI; line-boundary syntactic-unit tests.
- phase50_synthesis (629): grand synthesis; simplest generative model reproducing observed stats; Zipf fit.
- phase51_attack_synthesis (865): 5 skeptical attacks on the synthesis (char-level vs morphological structure; to_glyphs introduced).
- phase52_discriminators (548): burstiness B, mechanical-generation exclusion; writes results/phase52_output.txt (convention resumes).
- phase53_cipher_tests (633): cipher identification (JSD, char bigram entropy vs generated).
- phase54_natlang_vs_cipher (570): within-word vs between-word char predictability; natural language vs syllable cipher.
- phase55_vc_separation (645): Sukhotin's algorithm vowel/consonant inference; alternation rate; CV patterns.

## phase56-62 (cross-script/encoding-tournament era; pr() UTF-8 helper appears; eva_to_glyphs family)
- phase56_syllabary_test (764): syllabary hypothesis via Sukhotin+alternation vs generated corpora.
- phase57_bax_test (687): Bax/Vogt phonetic mapping test, edit distances vs N_RANDOM=1000.
- phase58_cross_script (859): VMS vs Gutenberg langs + embedded Japanese/Korean/Arabic/Hawaiian samples + cipher variants; **NETWORK (Gutenberg)**; writes results/phase58_output.json (consumed by 59+60).
- phase59_forward_model (871): 6 encoder models of Italian (syllabic/onset-rime/verbose-positional/abbrev/subst) → z-score distance to VMS; reads phase58_output.json (graceful fallback); NETWORK.
- phase60_positional_verbose (1081): verbose positional-zone cipher variants tuned; reads phase58 output; NETWORK.
- phase61_word_shape_validation (850): 12-discriminator word-shape battery vs optimized verbose cipher and simple subst; NETWORK.
- phase62_word_anatomy (975): zone MI decomposition (uses scipy? check), permutation MI tests, per-position MI curves. **imports scipy — may fail (not installed)**.

## phase63-72 (generative-discrimination era; stdout; mostly seed 42)
- phase63_codicological_coherence (1220): misbinding hypothesis tests (Lisa Fagin Davis 5-scribes); quire coherence metrics.
- phase64_encoding_tournament (886): generates synthetic texts per encoding model, 7-stat fingerprint tournament.
- phase65_reverse_engineer_script (864): character-merging transforms of Latin toward VMS entropy profile.
- phase66_glyph_resegmentation (910): data-driven glyph resegmentation (BPE-ish merges); H(c|prev)/H(c).
- phase67_run_length_morphology (986): run-length morphology of i/e chains; slot grammar.
- phase68_run_conditioned_transitions (781): run-conditioned transition matrices vs Currier A table.
- phase71_paragraph_initials (608): paragraph-initial glyph analysis + star marker correlation (f103r etc). no seed (deterministic counting).
- phase72_naibbe_calibration (1117): Naibbe verbose-cipher calibration, SEED=20250413, N_TABLES=30, TARGET_WORDS=36000; NETWORK (urllib for source texts).

## phase73-80 (abbreviation/paragraph/gallows-allograph era)
- phase73_abbreviation_model (1119): medieval abbreviation models (819 experiments cited in docs) vs VMS fingerprint; SEED=20250413; NETWORK.
- phase74_paragraph_framing (963): paragraph-initial/final consistency framing tests, SEED=42.
- phase75_latin_mapping (986): Latin paragraph-initial letter mapping (caesar.txt etc), VMS_TOTAL_PARAS=784; NETWORK fallback.
- phase76_vernacular_mapping (961): same for vernacular corpora (italian_cucina, german_faust, etc); NETWORK fallback.
- phase77_gallows_ecology (876) + phase77b_line_position_gallows (660): gallows distribution ecology; line-position gallows stats.
- phase78_allograph_test (796): p≡t, f≡k allograph hypothesis.
- phase79_gallows_collapse (708): collapse gallows allographs → true vocabulary size.
- phase80_abjad_hypothesis (717): vowel-stripping fingerprint comparison.

## phase81-85 (genre-fingerprint + chunk era)
- phase81_german_genre_fingerprint (935): German genre-matched (BVGS herbal etc) fingerprint vs VMS.
- phase82_charm_fingerprint (1126): German charm/incantation corpus fingerprint.
- phase82_line1_body_separation (1142): two encoding subsystems test (line-1 vs body).
- phase83_encoding_layer_sweep (871): parameter sweep of encoding layers (seed 83).
- phase83_subword_segmentation (1231): branching-entropy subword segmentation (chunk inventory origin).
- phase84_mi_meaning_area (804): MI(d) long-range decay (Montemurro-style), SPACE_TOKEN.
- phase85_chunk_fingerprint (1343): chunk-level fingerprint (MAX_CHUNKS=6) vs NL syllables — verdict scoring later corrected by 85R.
- phase85_pelling_verbose_cipher (1135): Pelling 2-layer abbrev+verbose bigram cipher test (seed 85).
- phase85R_revalidation (678): CORRECTIVE audit of 85 scoring (h_ratio framing).

## BUG #3 (confirmed): phase86_chunk_equivalence.py:1138-1139
- Step 10 NL cross-check references data/latin_texts/caesar_gallic_wars.txt + vernacular_texts/libro_della_cucina.txt; actual files are caesar.txt / italian_cucina.txt → check silently skipped. Fix in Phase 2 (output will gain Step 10 results; documented shift). 86R built partly because of this.

## phase86-91 (chunk-equivalence/spectral era; all seed 42; chunk-parser family parse_word_into_chunks/parse_one_chunk MAX_CHUNKS=6)
- phase86_chunk_equivalence (1378): chunk equivalence class discovery (k-collapse to alphabet); writes phase86_chunk_equivalence.json? (check — 6 scripts read it); HAS BUG #3.
- phase86R_revalidation (934): corrective — frequency-merge null model, collapse-artifact math.
- phase87_spectral_vc (1136): spectral V/C separation on chunk graph. phase87_gallows_null_test (879): gallows-as-nulls.
- phase87R_revalidation (734): audits 87 (purity metric, sign(0), null validity).
- phase88_position_identity (1129): position × identity decomposition of chunks.
- phase89_context_divergence (1277): cross-position context divergence of chunk identities.
- phase90_crossword_chunk_mi (1102): cross-word chunk MI.
- phase91_zodiac_galenic_axis (1080): zodiac label axis vs Galenic qualities (manual t-approx).

## phase92-97 (Currier/slot-regime era; chunk parser; seed 42)
- phase92_ae_minimal_pairs (1028): a↔e minimal pairs/substitution.
- phase93_currier_slot2_regime (964): Currier A/B as SLOT2 regime shift.
- phase94_e_extension_morphology (893): slot2 e-extension productivity.
- phase95_currier_split_fingerprint (727): independent A/B fingerprints.
- phase96_cluster_hchar (538): cluster-level h_char + source language matching. **HARDCODED ABSOLUTE PATH c:\projects\voynich_slop\folios (BUG/portability — fix Phase 2)**
- phase97_slot_grammar_hchar (812): slot grammar as h_char generative model; writes results/phase97_slot_grammar_hchar.json. **HARDCODED ABSOLUTE PATHS (FOLIO_DIR/LATIN_DIR/RESULTS_DIR)**

## phase98-107 (25-class alphabet / decipherment-attempt era; chunk parser, seed 42; write results/phaseNNN_*.{json,txt})
- phase98_generative_chunk_model (1075): generative chunk model; writes phase98 json+txt.
- phase99_script_typology (1147): script typology comparison.
- phase100_decipherment (1120): targeted decipherment w/ 25-class alphabet; READS results/phase86_chunk_equivalence.json.
- phase101_currier_ab_dichotomy (1386): A/B dichotomy resolution; manual logistic regression; READS phase86 json.
- phase102_historical_validation (1229): historical validation; READS phase86 json.
- phase103_positional_class_decomposition (1534): positional decomposition of 25-class alphabet.
- phase104_latin_ending_test (869): word-final chunks vs Latin inflection endings.
- phase105_cappelli_retest (932): Cappelli abbreviation marks vs VMS suffixes retest.
- phase106_abbreviation_decode (483) / 106b_bench_variants (256) / 106c_positional_freq_match (499): f1r decode attempts + positional frequency matching (unseeded but deterministic counting).
- phase107_slot_mi_decomposition (924): intra-chunk slot MI decomposition (z=1290-9190 finding cited in theories.md).

## Remaining pre-phase scripts already covered: all 131 accounted for.
