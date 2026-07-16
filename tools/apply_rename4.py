"""Rename pass 4: prose fossils of the old phase numbering.

The user-visible texts still said things like "84 phases of analysis",
"This phase tests", "Phases 32-38 established", and result JSONs carried
a numeric 'phase' metadata key. Generic rules + a hand-checked table.
"seasonal phase" in zodiac_galenic_axis is genuine domain vocabulary and
is left alone.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / 'scripts'

# hand-checked, file-specific replacements (applied before generic rules)
EDITS = {
 'ae_minimal_pairs.py': [
  ('glyph pattern in 91 phases.', 'glyph pattern found anywhere in the suite.')],
 'bax_decipherment_test.py': [
  ('positional profiles we established in Phases 36-56?',
   'positional profiles established across the morphology and hypothesis-testing analyses?')],
 'chunk_fingerprint.py': [
  ('84 phases of analysis have produced a PARADOX:',
   'The analyses so far have produced a PARADOX:')],
 'chunk_fingerprint_revalidation.py': [
  ('Prior phases report h_char = 0.641.', 'Earlier analyses report h_char = 0.641.')],
 'claims_correction_audit.py': [
  ('(standard from previous phases)', '(standard shared pipeline)')],
 'compound_decomposition.py': [
  ('Based on Phases 27-29 findings, propose a revised parse model.',
   'Based on the root-lexicon audit findings, propose a revised parse model.')],
 'compound_model_validation.py': [
  ('(same as prior phases)', '(same as prior tests)')],
 'cross_script_fingerprint.py': [
  ('(reuse from earlier phases)', '(shared with earlier tests)')],
 'cross_word_chunk_dependencies.py': [
  ('Phases 85-89 thoroughly characterized WITHIN-word chunk structure.',
   'The chunk-structure tests thoroughly characterized WITHIN-word chunk structure.')],
 'currier_dichotomy_resolution.py': [
  ('CRITICAL FIX: All prior phases (98, 100, ...) used a hardcoded',
   'CRITICAL FIX: All prior analyses (generative_chunk_model, chunk_alphabet_decipherment, ...) used a hardcoded'),
  ('"""The BROKEN hardcoded function from prior phases. Kept for comparison."""',
   '"""The BROKEN hardcoded function from prior analyses. Kept for comparison."""'),
  ('ALL prior A/B results (Phases 3, 63, 68, 98) are contaminated.',
   'ALL prior A/B results (currier_register_comparison, misbinding_coherence_test, run_conditioned_transitions, generative_chunk_model) are contaminated.')],
 'charm_incantation_fingerprint.py': [
  ('NEXT PHASE RECOMMENDATIONS:', 'FOLLOW-UP RECOMMENDATIONS:')],
 'encoding_layer_sweep.py': [
  ('94 phases have established ONE central unsolved anomaly:',
   'The suite has established ONE central unsolved anomaly:'),
  ('Phases 59-61 tested encoding transformations on Italian (Dante) only,',
   'forward_process_models, positional_verbose_cipher and word_shape_validation\ntested encoding transformations on Italian (Dante) only,')],
 'encoding_model_tournament.py': [
  ('63 phases of characterization. Time to DISCRIMINATE between models.',
   'Characterization is done. Time to DISCRIMINATE between models.')],
 'evidence_synthesis.py': [
  ('49 phases of statistical analysis. Time to ask: what kind of system',
   'A full battery of statistical analyses behind us. Time to ask: what kind of system'),
  ('print("  WHAT 49 PHASES HAVE ESTABLISHED:")',
   'print("  WHAT THE SUITE HAS ESTABLISHED:")')],
 'e_extension_morphology.py': [
  ('- Phases 91-93 measured SLOT2 at the MACRO level (per-folio averages).',
   '- The SLOT2 regime tests measured SLOT2 at the MACRO level (per-folio averages).')],
 'morphology_model_audit.py': [
  ('Phases 32-33 caught a suffix artifact that corrupted 4+ findings.',
   'suffix_split_artifact_test and suffix_bug_cascade_audit caught a suffix artifact that corrupted 4+ findings.')],
 'position_identity_decomposition.py': [
  ('NONE of these phases directly measured:', 'NONE of those tests directly measured:')],
 'root_lexicon_expansion.py': [
  ('New roots added this phase:', 'New roots added by this test:')],
 'root_lexicon_rosetta.py': [
  ("Now that we've decoded the STRUCTURE of the writing system (Phases 10-14):",
   "Now that we've decoded the STRUCTURE of the writing system (the preceding structural analyses):")],
 'sentence_translation.py': [
  ('2. Apply CONFIRMED DICTIONARY built from Phases 15-16',
   '2. Apply CONFIRMED DICTIONARY built from root_lexicon_rosetta and the Coptic probes'),
  ('# MORPHOLOGICAL PIPELINE (from Phases 10-15)',
   '# MORPHOLOGICAL PIPELINE (shared with the structural analyses)'),
  ('# CONFIRMED DICTIONARY — all verified mappings from Phases 15-16',
   '# CONFIRMED DICTIONARY — all verified mappings from root_lexicon_rosetta and the Coptic probes'),
  ('# ── Astronomical (Phases 15-16) ──', '# ── Astronomical mappings ──')],
 'spectral_vowel_consonant.py': [
  ('86 phases have established that VMS chunks are functional characters',
   'Prior analyses have established that VMS chunks are functional characters')],
 'vowel_consonant_separation.py': [
  ('This is the first DECIPHERMENT-oriented phase.',
   'This is the first DECIPHERMENT-oriented test.')],
 'word_functional_anatomy.py': [
  ('glyphs as atomic units, consistent with Phases 58-61.',
   'glyphs as atomic units, consistent with the encoding-model tests.')],
 'word_order_syntax_test.py': [
  ('Phases 32-38 established that INTRA-word morphological structure is real',
   'The morphology audits established that INTRA-word morphological structure is real')],
 'word_shape_validation.py': [
  ('Phases 58-60 matched VMS on 9/10 global summary statistics using a',
   'cross_script_fingerprint, forward_process_models and positional_verbose_cipher\nmatched VMS on 9/10 global summary statistics using a')],
 'zodiac_degree_semantics.py': [
  ('# ── Load ring_decan_results from previous Phase ─',
   '# ── Load ring_decan_results from ring_decan_mapping ─')],
 'zodiac_label_network.py': [
  ('This builds on all prior phases: label extraction (pipeline), cross-reference',
   'This builds on all prior analyses: label extraction (pipeline), cross-reference')],
 'zodiac_ring_alignment.py': [
  ('# Confirmed translations (from Phases 16-17)',
   '# Confirmed translations (from the Coptic probes and sentence_translation)')],
 'common/core.py': [
  ('"""Shared analysis helpers extracted verbatim from the phase scripts.',
   '"""Shared analysis helpers extracted verbatim from the test scripts.'),
  ('pre-phase-19 scripts used the project root while later scripts and the',
   'the earliest scripts used the project root while later scripts and the')],
}

changed = set()
for fname, pairs in EDITS.items():
    p = S / fname
    text = p.read_text(encoding='utf-8', errors='replace')
    for old, new in pairs:
        if old not in text:
            print(f'MISS {fname}: {old[:55]!r}')
            continue
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    changed.add(p.stem)

# generic rules over every script
for p in sorted(S.glob('*.py')):
    text = p.read_text(encoding='utf-8', errors='replace')
    orig = text
    text = text.replace('This phase', 'This test').replace('this phase', 'this test')
    text = text.replace('THIS PHASE', 'THIS TEST')
    text = text.replace('#  ANALYSIS PHASES', '#  ANALYSIS STEPS')
    text = re.sub(r'^# PHASES$', '# STEPS', text, flags=re.M)
    # result-JSON metadata key: 'phase': <num or str> -> 'test': '<stem>'
    text = re.sub(r"'phase':\s*(?:\d+|'[^']*')", f"'test': '{p.stem}'", text)
    text = re.sub(r'"phase":\s*(?:\d+|"[^"]*")', f'"test": "{p.stem}"', text)
    if text != orig:
        p.write_text(text, encoding='utf-8')
        changed.add(p.stem)

# README_WEBUI.md offline note
p = ROOT / 'README_WEBUI.md'
t = p.read_text(encoding='utf-8', errors='replace')
t = t.replace('so phases 58-65 and 72-73 run fully offline',
              'so the Gutenberg-dependent tests run fully offline')
p.write_text(t, encoding='utf-8')

print('scripts changed:', len(changed))
Path(ROOT / 'tools' / '_pass4_changed.txt').write_text(
    ','.join(sorted(changed - {'core'})), encoding='utf-8')

# final audit: every remaining 'phase' word in live surfaces
left = []
for p in list(S.glob('*.py')) + list((S / 'common').glob('*.py')) \
        + list((ROOT / 'webui').glob('*.py')) + [ROOT / 'README_WEBUI.md', ROOT / 'README.md']:
    for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if re.search(r'(?i)\bphases?\b', line):
            left.append(f'{p.name}:{i}: {line.strip()[:85]}')
print('\nremaining (should be domain-legit only):')
for l in left:
    print(' ', l)
