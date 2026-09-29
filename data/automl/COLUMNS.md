# AutoML CSV columns (muffin vs chihuahua)

Each row = one fake example. Scores are 0–1 (“not at all” → “a lot”).

| Column | Meaning (FR) | Muffin tends to… | Chihuahua tends to… |
|--------|--------------|------------------|---------------------|
| `pointy_ears` | oreilles pointues | bas | haut |
| `has_fur` | fourrure / poils | bas | haut |
| `looks_like_pastry` | ressemble à un gâteau | haut | bas |
| `round_shape` | forme ronde | haut | bas |
| `brown_like_crust` | brun comme une croûte | haut | variable / bas |
| `cute_eyes` | yeux mignons (chien) | bas | haut |
| **`label`** | **réponse à prédire** | `muffin` | `chihuahua` |

AutoML learns: given the scores, predict `label`.
