---
name: heirloom-audit-learning-visualisation
description: "Audit an educational chart, diagram or interactive visual for mathematical fidelity, evidence scope, causal implications and accessibility. Use when a lesson's visual may mislead or fail at its actual viewport; use media-deliverable verification for a broader exported video/document and statistical teaching for the lesson content itself."
---
# Audit a learning visualisation

Check whether the visual communicates the intended mechanism without adding unsupported claims through scale, animation or missing context.

## Establish the learning and data contract

Collect the source data/equations, learning objective, visual source/export, intended audience, target devices and explanation text. Identify the exact claim each encoded mark is meant to support. If the underlying data or model is missing, inspect layout and interpretation provisionally while marking numerical fidelity GAP; do not infer the source from a polished chart.

Separate observed data, modeled outputs and hypothetical controls in legends and captions. Retain sample counts, units, denominator and uncertainty assumptions. If a simulation is synthetic, the label should remain visible when the visual is exported or viewed apart from the lesson.

## Inspect the encoding and interaction

1. Recalculate representative values independently from the retained source. Check axes, category order, percent conversion, units and aggregation. Distinguish missing data from zero and check whether clipping hides valid values or uncertainty.
2. Verify the visual scale matches the intended comparison. A truncated baseline may amplify small differences; a logarithmic scale requires an applicable domain and explicit explanation. Area/volume encodings must correspond to the value, not an unintended squared impression.
3. Check arrows, sequencing and animation for causal implications. Co-occurrence or a moving model curve does not establish that an intervention causes an observed outcome. State model assumptions and causal gaps in the explanatory layer.
4. For sliders or branching controls, inspect extremes, invalid inputs and boundary gates. Compare displayed labels and exported values with the same calculation. A disabled/deferred policy should not retain a success-looking bar from its previous state.
5. Inspect actual desktop and narrow/mobile layouts when tools exist. Check legibility, overflow, color-independent distinctions, keyboard/focus behavior and text alternatives for essential content. If only source/export is available, label device interaction untested instead of claiming accessibility from CSS.
6. Test the visual's pedagogic task: can a learner identify the intended distinction and the relevant limitation without reading hidden implementation details? Use a small interpretation prompt where a wrong-but-plausible conclusion exposes misleading encoding.

## Deliver and verify

Produce `visual_findings.md` with source references, screenshots or exact element locations, independent calculations, severity basis, patches and remaining device/data gaps. For an interactive visual, retain boundary fixtures and downloaded result comparisons. Preserve user originals and edit a copy unless the task authorises the source change.

Accept a known-value positive case and an adversarial case with missing values, an extreme control or a misleading denominator. A simulated mobile viewport must be identified as emulation, not an actual iPhone test. Passing supports fidelity and usability under the inspected conditions; it does not prove the lesson caused learning.

Worked situation: an ensemble chart shows90% success after its budget gate defers every task. Clear the effective-success encoding and label the model's ungated expectation separately. Otherwise the attractive bar teaches that unaffordable work still succeeded.
