# Multilingual Sentiment Analysis for Kazakh & Russian Reviews

Binary sentiment classification (positive / negative) for user reviews written in **Kazakh, Russian, or a mix of both**. The system combines classical TF-IDF baselines with transformer models and uses a **language-routing strategy** at inference time — each review is sent to the model best suited for its detected language.

This is the final project for the *Text Classification* track. The applied target is a real Kazakhstan-specific dataset (2GIS reviews).

---

## Project structure

```
.
├── data/                  # raw and processed datasets (KazSAnDRA, RU sentiment, 2GIS)
├── models/                # fine-tuned model checkpoints (see "Models" section)
├── notebooks/
│   ├── ml-final-data-preprocessing.ipynb   # cleaning, undersampling, splits
│   ├── baseline_models.ipynb               # TF-IDF + Ridge / SGD / fastText
│   ├── transformers.ipynb                  # mBERT (kk), ruBERT-tiny2 (ru), mBERT (all)
│   └── ml-final-inference.ipynb            # language-routed inference pipeline
├── parser/                # 2GIS review collection scripts
├── predictions.csv        # output of the inference pipeline on the 2GIS dataset
└── Documentation.docx     # full project report
```

---

## Datasets

| Dataset | Language | Role |
|---|---|---|
| **KazSAnDRA** (ISSAI / Nazarbayev University) | Kazakh | Training & validation for the Kazakh model |
| **Russian Sentiment Dataset** (Kaggle, `mar1mba`) | Russian | Training & validation for the Russian model |
| **Combined corpus** (KazSAnDRA + RU) | kk + ru | Training the multilingual fallback |
| **2GIS reviews** (parsed) | kk / ru / mixed | Real-world Kazakhstan evaluation set |

Each example carries a `lang_label` (`kk` / `ru`) used for stratification and routing. Both source datasets are imbalanced toward positive reviews and toward Russian; we apply two-stage undersampling (Russian-vs-Kazakh balance, then positive-vs-negative within the Kazakh subset) only on the training split.

---

## Models

### Baselines (TF-IDF + linear classifier)

Trained on the combined Kazakh + Russian corpus without routing.

| Model | Notes |
|---|---|
| Word TF-IDF + RidgeClassifier | unigrams + bigrams |
| Word TF-IDF + SGDClassifier | linear SVM, hinge loss |
| Word + Char TF-IDF + Ridge | best baseline — char n-grams capture morphology |
| Word + Char TF-IDF + SGD | combined features, SGD |
| fastText supervised | lightweight neural baseline |

### Transformers (language-routed)

Fine-tuned with the Hugging Face `Trainer` API, early stopping on macro F1.

| Model | Base checkpoint | Trained on | Role at inference |
|---|---|---|---|
| **mBERT (kk)** | `bert-base-multilingual-cased` | Kazakh subset only | Route for Kazakh-dominant text |
| **ruBERT-tiny2 (ru)** | `cointegrated/rubert-tiny2` | Russian subset only | Route for Russian text |
| **mBERT (all)** | `bert-base-multilingual-cased` | Combined corpus | Fallback for mixed / unknown |

---

## Results

Held-out validation split (15% of the training corpus). **Macro F1** is the primary metric.

| Model | Accuracy | F1 macro | ROC-AUC | Notes |
|---|---|---|---|---|
| Word TF-IDF + Ridge | 0.8431 | 0.8431 | — | Baseline |
| Word TF-IDF + SGD | 0.8429 | 0.8429 | — | Baseline |
| **Word + Char TF-IDF + Ridge** | **0.8472** | **0.8472** | — | **Best baseline** |
| Word + Char TF-IDF + SGD | 0.8459 | 0.8459 | — | Baseline |
| fastText supervised | 0.8256 | 0.8256 | — | Baseline |
| mBERT (kk only) | 0.8364 | 0.8364 | 0.9042 | Transformer |
| **ruBERT-tiny2 (ru only)** | **0.8787** | **0.8787** | **0.9504** | **Best overall** |
| mBERT (all languages) | 0.8531 | 0.8531 | 0.9275 | Transformer / fallback |

**Takeaways**

- Strong TF-IDF baselines (especially with char n-grams) are already competitive — solid lower bound.
- The biggest gain from transformers comes on **Russian** data (ruBERT-tiny2: +3.1 acc, +0.05 ROC-AUC over the best baseline).
- mBERT on Kazakh roughly matches TF-IDF — mBERT has limited Kazakh coverage in pretraining.
- Routing each review to a language-specific model beats any single multilingual model.

---

## Inference pipeline

For each raw review:

1. **Clean / normalize** — strip whitespace, drop empties/duplicates, cast to `str`.
2. **Detect language** — assign `lang_label ∈ {kk, ru, other}`. Original implementation used a Kazakh-character heuristic; the current notebook uses **lingua** (more robust on short / code-switched text).
3. **Route to model:**
   - `kk` → `models/mbert_kk/best_model`
   - `ru` → `models/rubert_ru/best_model`
   - `other` → `models/mbert_all_languages/best_model` (fallback)
4. **Predict** sentiment + softmax confidence of the predicted class.
5. **Aggregate** results (overall distribution, per-language breakdown).

Output: `predictions.csv` with columns `text, lang_label, pred_label, pred_prob, pred_sentiment`.

### Quick start

```bash
pip install transformers torch pandas tqdm lingua-language-detector scikit-learn
```

Then open `notebooks/ml-final-inference.ipynb` and run all cells. Make sure the three fine-tuned checkpoints exist under `models/`.

---

## Limitations

- **Class & language imbalance** persists even after undersampling — more positives than negatives, more Russian than Kazakh.
- **Kazakh coverage in mBERT is limited**, capping performance on the Kazakh subset.
- **Language detection is imperfect** on very short or code-switched reviews; mixed Kazakh/Russian text can be misrouted.
- **Domain shift** — training data (KazSAnDRA, Kaggle RU) differs in style from 2GIS reviews.
- **Label noise** — binary labels derived from star ratings collapse neutral / mixed reviews into pos/neg.
- **Limited tuning** — 3-epoch fine-tunes, default hyperparameters, no cross-validation.

---

## Future work

- Replace heuristic LID with **lingua** or a fastText LID model end-to-end; explicit handling of code-switching.
- Use a **Kazakh-specific model** (KazBERT, continued mBERT pretraining on KazSAnDRA).
- **Class-weighted / focal loss**, text augmentation (back-translation, synonym replacement).
- Collect more labeled 2GIS data; calibrate thresholds on the Kazakhstan domain.
- Systematic **error analysis** + interpretability (attention, SHAP over TF-IDF features).

---

## References

- Yeshpanov, R. & Varol, H. A. *KazSAnDRA: Kazakh Sentiment Analysis Dataset of Reviews and Attitudes.* ISSAI / Nazarbayev University.
- *Russian Sentiment Dataset* — Kaggle (mar1mba).
- Wang, Z., Karthikeyan, K., Mayhew, S., & Roth, D. *Extending Multilingual BERT to Low-Resource Languages.*
- Gessler, L. & Zeldes, A. *MicroBERT: Effective Training of Low-Resource Monolingual BERTs through Parameter Reduction and Multitask Learning.* ACL Anthology.
- fastText — [Language identification](https://fasttext.cc/docs/en/language-identification.html).
- [lingua-language-detector](https://github.com/pemistahl/lingua-py).

---

## Authors

Sanzhar Altynbay — Computer Science, Kazakhstan
Final project — Text Classification track
