"""Reproduce the NeoX continuous synthetic-data calibration.

Requires numpy, scikit-learn and matplotlib. Run:
    python train_ml_model.py
Fits only on the fixed 800-row training split; never on the held-out 200 rows.
The output is for experimental demonstration, not clinical use.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

BASE = Path(__file__).resolve().parent
DATASET = BASE / 'Neo_X_Continuous_1000_Dataset.csv'
with DATASET.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 1000, f'Expected 1000 rows; got {len(rows)}'
required = {'Sample_ID', 'Tartrazine_mM', 'Bili_Equiv_mg_dL', 'Skin_Tone', 'S_Blue', 'S_Melanin', 'S_Corrected'}
assert required.issubset(rows[0]), 'Missing required CSV columns'
x = np.array([[float(r['S_Blue']), float(r['S_Melanin'])] for r in rows])
y = np.array([float(r['Bili_Equiv_mg_dL']) for r in rows])
tones = np.array([r['Skin_Tone'] for r in rows])
train_idx, test_idx = train_test_split(
    np.arange(len(rows)), test_size=0.2, random_state=42, stratify=tones
)
model = LinearRegression().fit(x[train_idx], y[train_idx])
intercept, blue_coef, mel_coef = float(model.intercept_), *map(float, model.coef_)
# The deployed two-feature OLS is exactly equal to intercept + blue_coef*(blue + k*melanin).
k = mel_coef / blue_coef
pred = model.predict(x)
corrected = x[:, 0] + k * x[:, 1]
residual = pred - y

def metrics(indices):
    yp = pred[indices]
    return {
        'n': len(indices),
        'r2': float(r2_score(y[indices], yp)),
        'rmse_mg_dL': float(np.sqrt(mean_squared_error(y[indices], yp))),
        'mae_mg_dL': float(mean_absolute_error(y[indices], yp)),
    }

train_metrics = metrics(train_idx)
test_metrics = metrics(test_idx)
all_metrics = metrics(np.arange(len(rows)))
by_tone = {t: metrics(np.array([i for i in test_idx if tones[i] == t])) for t in ('Fair', 'Medium', 'Dark')}
error_band = 1.96 * test_metrics['rmse_mg_dL']  # illustrative only; NOT a clinical interval
record = {
    'dataset': DATASET.name,
    'samples': len(rows),
    'features': ['S_Blue', 'S_Melanin'],
    'target': 'Bili_Equiv_mg_dL',
    'method': 'two-feature ordinary least squares (linear regression)',
    'validation': '80/20 stratified split by Skin_Tone, random_state=42',
    'model': {
        'intercept': intercept,
        'coef_blue': blue_coef,
        'coef_melanin': mel_coef,
        'correction_k': k,
        'formula': 'estimated_mg_dL = intercept + coef_blue * (S_Blue + correction_k * S_Melanin)'
    },
    'train': train_metrics,
    'test': test_metrics,
    'all': all_metrics,
    'test_by_skin_tone': by_tone,
    'illustrative_error_band_plus_minus_mg_dL': error_band,
    'limitations': [
        'Synthetic data only; not patient, clinical, or hardware validation.',
        'The uploaded S_Corrected is NOT the fitted model correction and is preserved separately.',
        'No inference about real-world generalization, treatment, or diagnostic safety.',
    ],
}
(BASE / 'neox_model.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')

is_test = np.zeros(len(rows), dtype=bool)
is_test[test_idx] = True
output_fields = ['Sample_ID','Tartrazine_mM','Bili_Equiv_mg_dL','Skin_Tone',
                 'S_Blue','S_Melanin','Source_S_Corrected','Model_S_Corrected',
                 'ML_Predicted','Residual_PredMinusActual','Split']
with (BASE / 'neox_calibration_dataset.csv').open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=output_fields)
    writer.writeheader()
    for i, row in enumerate(rows):
        writer.writerow({
            'Sample_ID': row['Sample_ID'],
            'Tartrazine_mM': row['Tartrazine_mM'],
            'Bili_Equiv_mg_dL': row['Bili_Equiv_mg_dL'],
            'Skin_Tone': row['Skin_Tone'],
            'S_Blue': row['S_Blue'],
            'S_Melanin': row['S_Melanin'],
            'Source_S_Corrected': row['S_Corrected'],
            'Model_S_Corrected': f'{corrected[i]:.8f}',
            'ML_Predicted': f'{pred[i]:.8f}',
            'Residual_PredMinusActual': f'{residual[i]:.8f}',
            'Split': 'test' if is_test[i] else 'train',
        })

try:
    import matplotlib.pyplot as plt
except ImportError:
    print('matplotlib missing: calibration PNG not regenerated')
else:
    fig, ax = plt.subplots(figsize=(11, 6.6), dpi=140)
    colors = {'Fair': '#60a5fa', 'Medium': '#f59e0b', 'Dark': '#f87171'}
    for tone, color in colors.items():
        select = tones == tone
        ax.scatter(corrected[select], y[select], color=color, alpha=.57, s=13,
                   linewidths=0, label=f'{tone} ({select.sum()})')
    xs = np.linspace(corrected.min(), corrected.max(), 250)
    ax.plot(xs, intercept + blue_coef * xs, color='#584bd5', lw=2.6,
            label='Model fitted on 800 training samples')
    ax.set(xlabel='Model-corrected signal (S_Blue + k × S_Melanin)',
           ylabel='Synthetic bilirubin equivalent (mg/dL)',
           title=f'NeoX | 1,000 Continuous Synthetic Calibration Samples  •  Holdout R² = {test_metrics["r2"]:.4f}')
    ax.legend(loc='upper right', framealpha=.95)
    ax.grid(alpha=.18)
    fig.tight_layout()
    fig.savefig(BASE / 'neox_calibration_curve_1000.png', dpi=160)
    plt.close(fig)

print('NeoX continuous synthetic dataset: 1000 rows')
print(f'Bili_equivalent = {intercept:.9f} + ({blue_coef:.9f} × S_Blue) + ({mel_coef:.9f} × S_Melanin)')
print(f'Equiv: S_model_corrected = S_Blue + ({k:.9f} × S_Melanin)')
for name, metric in [('Train', train_metrics), ('Holdout test', test_metrics), ('All samples', all_metrics)]:
    print(f'{name:14s}: n={metric["n"]} R²={metric["r2"]:.6f}, RMSE={metric["rmse_mg_dL"]:.6f}, MAE={metric["mae_mg_dL"]:.6f}')
print('All metrics/coefficients written to neox_model.json. Not clinical validation.')
