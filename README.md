NeoX DASHBOARD — CONTINUOUS 1000-POINT TRAINED MODEL + LIVE ESP32
==============================================================

CONTENTS
  neox_dashboard.html               Updated dashboard with live ESP32 GET /data
  Neo_X_Continuous_1000_Dataset.csv Exact user-supplied dataset (unchanged)
  neox_calibration_dataset.csv     1,000 predictions / residuals / train-test labels
  neox_calibration_curve_1000.png  Offline calibration plot (all samples)
  neox_model.json                  Trained parameters and train/test metrics
  train_ml_model.py                Reproducible training, split and exports
  README.txt                       This file

TRAINING: CONTINUOUS SYNTHETIC CALIBRATION
  Samples:        1,000 synthetic continuous rows
  Split:          800 training / 200 held-out test (random_state=42;
                  split stratified by skin tone)
  Features:       S_Blue, S_Melanin
  Target:         Bili_Equiv_mg_dL
  Estimator:      ordinary least squares linear regression (two features)
  Fitted on:      training rows only (test rows not used to fit coefficients)

  Bili_equiv = 43.771318833 - 43.113747128*S_Blue - 7.232630861*S_Melanin

  Equivalently:
    S_model_corrected = S_Blue + 0.167756953*S_Melanin
    Bili_equiv = 43.771318833 - 43.113747128*S_model_corrected

  Training (800): R² = 0.995481; RMSE = 0.395264; MAE = 0.316305 mg/dL
  Test (200):     R² = 0.994845; RMSE = 0.407572; MAE = 0.327171 mg/dL

  Fair skin test:   68 samples, RMSE 0.394244 mg/dL
  Medium skin test: 69 samples, RMSE 0.454986 mg/dL
  Dark skin test:   63 samples, RMSE 0.364497 mg/dL

SOURCE FIELD VS FITTED CORRECTION (IMPORTANT)
  The original supplied CSV includes a column called S_Corrected; its values
  follow a DIFFERENT calculation than the best-fitting new model correction.
  Neither that original column nor the uploaded data is modified.
  In neox_calibration_dataset.csv, 'Source_S_Corrected' is the original column
  and 'Model_S_Corrected' is recalculated using the trained coefficients.
  The dashboard plot and predictions use 'Model_S_Corrected'.
  The UI's Export Calibration CSV includes both columns and train/test split.

OPENING THE DASHBOARD
  1. Extract ZIP; open neox_package/neox_dashboard.html in a browser.
  2. Use the Calibration Curve tab to see all 1,000 colored sample points.
  3. Search / page by sample ID, skin tone, or train/test and export its CSV.
  4. In ML Prediction, enter S_Blue and S_Melanin for manual estimation.
  5. For real ESP32 readings, power compatible NeoX firmware, connect to
     NeoX_Sensor Wi-Fi and press 'Take reading' in Dashboard.
     Endpoint: http://192.168.4.1/data
     JSON numeric fields required: blue, melanin
     Optional: dB, dG, dRr, amb
     ESP32 firmware must implement GET /data and CORS (Access-Control-Allow-Origin: *).
     Network errors are displayed; the dashboard does not fabricate readings.
     An HTTPS-hosted dashboard may block the ESP32 HTTP request as mixed content.

  Chart.js v4.4.0 is currently loaded from cdnjs.cloudflare.com. With no
  internet available, live charts might not initialize. Offline plot PNG is
  included. Keep an internet connection for initial Chart.js load/cache.

REPRODUCE TRAINING
  pip install numpy scikit-learn matplotlib
  cd neox_package
  python train_ml_model.py
  This overwrites neox_model.json, neox_calibration_dataset.csv and the PNG
  using the same deterministic train/test split.
  It does not automatically edit the coefficients embedded in the HTML.
  (The shipped HTML already has the matching trained coefficients.)

SAFETY / LIMITATIONS
  These are synthetic data, NOT clinical measurements or independent hardware
  validation. Good held-out performance on synthetic data does not establish
  real-sensor or real-patient accuracy, generalizability or safety.
  Do not use the prototype for diagnosing jaundice, advising phototherapy or
  replacing confirmatory medical tests. All numeric bands and error ranges
  are research demonstrations, not neonatal treatment thresholds or clinical
  prediction intervals. The on-device firmware was not modified or verified.
