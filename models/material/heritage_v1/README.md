# Heritage Material Classification Model (Unvalidated Prototype)

> [!WARNING]
> **UNVALIDATED PROTOTYPE — DO NOT CITE AS RESEARCH RESULT**
> This model was trained on exploratory color- and contrast-augmented texture crops from masonry photographs, not genuine petrographic field samples.
> On independent validation data, this model achieved 25.0% accuracy (matching random guessing across 4 classes). Its predictions MUST NOT be cited or presented as authenticated heritage conservation research findings.

## Model Details
- **Architecture**: `MobileNetV3-Small` (PyTorch)
- **Target Classes**: `brick`, `granite`, `lime_mortar`, `sandstone`
- **Training Epochs**: 3
- **Device**: CPU
- **Validation Status**: `UNVALIDATED_PROTOTYPE`
- **Is Validated**: `False`
- **Is Demo / Prototype**: `True`

## Evaluation Metrics (Genuinely Computed, Not Fabricated)
- **Overall Accuracy**: 25.00%
- **Macro F1-Score**: 0.1000
- **Total Evaluated Samples**: 20 (5 per class)
- **Confusion Matrix**: All 20 samples predicted as "granite" due to underfitting on small synthetic crop set.

## Next Steps for True Research Validation
To validate this component for genuine scientific publication:
1. Acquire a verified petrographic heritage dataset (e.g., SEM/optical petrography of heritage stones, minimum 200+ samples per class).
2. Document geological sourcing, mineralogical composition, and surface patina.
3. Retrain with transfer learning from ImageNet or a domain-specific mineral database.
