# Semantic Precision Regression Report

- generated_at: 2026-02-11T03:12:37.294422+00:00
- case_count: 8
- passed_cases: 8
- failed_cases: 0
- case_pass_rate: 1.0
- expected_hit_rate: 1.0
- forbidden_violations: 0

## Case: cond_then_boundary
- description: condition scope should stop before then-clause consequence
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: negated_prefix_en
- description: english not-prefix should become negated slot value
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: double_negation_flag
- description: double-negation on negative flag should not emit false
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: coref_en_it
- description: cross-sentence it= should resolve to previous slot
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: coref_zh_alias
- description: Chinese pronoun alias should resolve to previous slot
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: scoped_coref
- description: coreference inside conditional scope keeps cond prefix
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: counterfactual_negation
- description: counterfactual negation should remain scoped
- passed: True
- missing_expected: []
- forbidden_violations: []

## Case: conditional_flag_isolation
- description: conditional flag should not leak into factual namespace
- passed: True
- missing_expected: []
- forbidden_violations: []
