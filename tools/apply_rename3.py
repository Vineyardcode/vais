"""Rename pass 3: hand-checked replacements for the 47 residual lines.

Each entry was resolved by reading its context; predecessor experiments
that no longer exist as scripts (old phases 10, 11, 18, 69, 70C, 82) are
reworded as prose instead of dangling numbers. Internal per-script
pipeline functions become partN_*.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / 'scripts'

EDITS = {
 'abbreviation_shorthand_model.py': [
  ('MOTIVATION (from Phase 70C and 72):',
   'MOTIVATION (from earlier shorthand experiments and naibbe_cipher_calibration):')],
 'astro_label_pipeline.py': [
  ('using the bimodal y-fraction criterion from Phase 1.',
   'using the bimodal y-fraction criterion from astro_crossref.')],
 'branching_entropy_segmentation.py': [
  ('Phase 53d measured positional entropy within words.',
   'cipher_identification_tests (part d) measured positional entropy within words.')],
 'chunk_fingerprint_revalidation.py': [
  ('Canonical Phase 82 value: 0.641 (likely method C or similar)',
   'Previously reported value: 0.641 (likely method C or similar)')],
 'controls_foundry.py': [
  ('controls_foundry — Controls Foundry (research charter, Phase 0)',
   'Controls Foundry — deterministic control corpora for the research charter (RESEARCH.md)')],
 'coptic_dictionary_probe.py': [
  ('# PHONETIC CORRESPONDENCE RULES (from Phase 16a Leo anchor)',
   '# PHONETIC CORRESPONDENCE RULES (from the Leo-anchor phonetic analysis)')],
 'currier_dichotomy_resolution.py': [
  ('(generative_chunk_model baselines, Phase 3, misbinding_coherence_test',
   '(generative_chunk_model baselines, currier_register_comparison, misbinding_coherence_test')],
 'diacritic_audit.py': [
  ('Phase 10 gallows-as-determinative finding, Hebrew niqqud analogy.',
   'the earlier gallows-as-determinative finding, Hebrew niqqud analogy.')],
 'egyptian_connection.py': [
  ('# True prefixes (from Phase 11 corrections)',
   '# True prefixes (from the corrected prefix inventory)')],
 'f66r_analysis.py': [
  ('print("  Combining Phase 1 evidence (root type, suffix class, section preference)")',
   'print("  Combining freq_rank_mapping evidence (root type, suffix class, section preference)")'),
  ('# Prefix meaning from Phase 1',
   '# Prefix meaning from freq_rank_mapping')],
 'gallows_semantics.py': [
  ('Phase 10 showed bench concentrate in herbal/pharma — do they also',
   'Earlier analysis showed benches concentrate in herbal/pharma — do they also')],
 'hebrew_deep_analysis.py': [
  ('Phase 2 of the Hebrew hypothesis investigation.',
   'Second stage of the Hebrew hypothesis investigation (follows hebrew_comparison).')],
 'high_frequency_root_profiles.py': [
  ('# Classification rules (from Phase 21b findings):',
   '# Classification rules (from zodiac_element_vocabulary part-b findings):')],
 'historical_validation.py': [
  ('- Genre fingerprinting failed in Phase 69/76 — recipe texts were',
   '- Genre fingerprinting has failed in earlier experiments — recipe texts were'),
  ('"Phase 4 features; genre scores 7/10; Widemann context; illustrations"',
   '"historical_pharma_comparison features; genre scores 7/10; Widemann context; illustrations"')],
 'hypothesis_discriminators.py': [
  ('Phase 51d used morphological decomposition (now known to be mostly',
   'synthesis_stress_test (part d) used morphological decomposition (now known to be mostly')],
 'naibbe_cipher_calibration.py': [
  ('# WORD BOUNDARY INFORMATION TEST (from Phase 53e)',
   '# WORD BOUNDARY INFORMATION TEST (from cipher_identification_tests part e)')],
 'parser_free_word_classes.py': [
  ('# Three-class system from Phase 43c clustering',
   '# Three-class system from word_class_robustness part-c clustering')],
 'root_lexicon_translation.py': [
  ('# Phase 18 (Zodiac names)',
   '# Zodiac names (from the zodiac ring analyses)')],
 'root_type_grammar.py': [
  ('PHASE 1 DEEP DIVE',
   'ROOT-TYPE GRAMMAR — the substance/process root split'),
  ('print("SYNTHESIS — PHASE 1 DEEP DIVE")',
   'print("SYNTHESIS — ROOT-TYPE GRAMMAR")')],
 'root_type_stress_test.py': [
  ('PHASE 1 DEEP DIVE',
   'ROOT-TYPE STRESS TEST — positional behavior of the two root types')],
 'syntactic_grammar_map.py': [
  ('Phase 40 proved syntax is real (z=80-128, survives all attacks).',
   'syntax_artifact_attack proved syntax is real (z=80-128, survives all attacks).')],
 'word_class_robustness.py': [
  ("Phase 42b's null shuffled random subsets, preserving GLOBAL marginals.",
   "two_class_section_grammar's part-b null shuffled random subsets, preserving GLOBAL marginals."),
  ('print("    Phase 42b found z=49-92, but the null preserved GLOBAL marginals.")',
   'print("    two_class_section_grammar part b found z=49-92, but the null preserved GLOBAL marginals.")'),
  ('# Define the bigrams to test (from Phase 42c)',
   '# Define the bigrams to test (from two_class_section_grammar part c)')],
 'zodiac_degree_semantics.py': [
  ('whichever shows highest variance ratio in Phase 5 (above).',
   'whichever shows highest variance ratio in Part 5 (above).  ')],
 'zodiac_ring_alignment.py': [
  ("Phase 18 proved root='e' is a parsing artifact from collapse_echains().",
   "Earlier analysis proved root='e' is a parsing artifact from collapse_echains().")],
}

for fname, pairs in EDITS.items():
    p = S / fname
    text = p.read_text(encoding='utf-8', errors='replace')
    for old, new in pairs:
        if old not in text:
            print(f'  MISS: {fname}: {old[:60]!r}')
            continue
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

# internal pipeline function names: phase_N_x / phaseNN_x -> part...
for p in sorted(S.glob('*.py')):
    text = p.read_text(encoding='utf-8', errors='replace')
    orig = text
    text = re.sub(r'\bphase_([0-9])_(?=[a-z])', r'part_\1_', text)
    text = re.sub(r'\bphase([0-9]{1,2})_(?=[a-z])', r'part\1_', text)
    if text != orig:
        p.write_text(text, encoding='utf-8')

# final residual check over everything live
count = 0
files = sorted(S.glob('*.py')) + sorted((S / 'common').glob('*.py')) \
    + sorted((ROOT / 'webui').glob('*.py')) + [ROOT / 'webui' / 'presets.json'] \
    + sorted((ROOT / 'sanity_checks').glob('*.py')) + [ROOT / 'README_WEBUI.md'] \
    + [ROOT / 'tools' / 'run_baseline.py', ROOT / 'tools' / 'rewrite_scripts.py']
for path in files:
    for i, line in enumerate(
            path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if re.search(r'(?i)\bphase\s*_?\d', line):
            print(f'  {path.relative_to(ROOT)}:{i}: {line.strip()[:100]}')
            count += 1
print(f'FINAL residual: {count} lines')
