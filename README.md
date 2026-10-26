# NeoX — Optical Neonatal Jaundice Screening Research

NeoX explores a portable, non-invasive optical approach to neonatal jaundice screening. This repository documents the initial ESP32-based prototype, a proposed STM32/MAX86916 hardware design, editable probe CAD, and a dashboard with a synthetic-data regression demonstration.

> **Research prototype:** NeoX is not a clinically validated diagnostic device. The included synthetic dataset and model metrics do not establish bilirubin accuracy in newborns. Do not use its outputs for diagnosis, treatment decisions or replacement of established bilirubin testing.

## Development status

| Area | Files / platform | Status |
|---|---|---|
| Initial optical prototype | ESP32 + TCS34725 + external RGB LEDs | Firmware included; hardware operation must be verified on the actual setup |
| Proposed optical hardware | STM32 + MAX86916 evaluation hardware | Schematic/design work; matching STM32 firmware is not included |
| Probe mechanics | SolidWorks assembly, three native parts and STEP exports | Editable probe geometry included; assembly references and physical fit require verification |
| Dashboard and model | HTML dashboard, Python training script, CSV and JSON files | Synthetic-data demonstration with an ESP32 HTTP interface |
| Complete handheld controller | Display, physical keypad, rechargeable power and replaceable probe concept | Full enclosure CAD and integrated implementation are not included in this snapshot |
| Clinical performance | Newborn bilirubin screening | Not established |

**The included Arduino sketch is for ESP32 + TCS34725. It does not operate the proposed STM32 + MAX86916 system.**

## Repository contents

| File | Description |
|---|---|
| `README.md` | Project overview, setup and limitations |
| `NeoX_TCS34725_WiFi.ino` | ESP32 firmware for TCS34725 measurements and a Wi-Fi HTTP endpoint |
| `neox_dashboard.html` | Browser dashboard, calibration plots and model demonstration |
| `Neo_X_Continuous_1000_Dataset.csv` | Supplied 1,000-row synthetic dataset |
| `neox_calibration_dataset.csv` | Model predictions, residuals and training/test labels |
| `neox_model.json` | Regression coefficients and saved evaluation metrics |
| `neox_calibration_curve_1000.png` | Exported calibration visualization |
| `train_ml_model.py` | Script to reproduce the synthetic-data model and exports |
| `neox.kicad_sch` | Proposed hardware schematic saved by KiCad 10.0 |
| `Assem1.SLDASM` | SolidWorks probe assembly |
| `Base.SLDPRT` / `Base.STEP` | Probe base native model and neutral export |
| `Optical Ring-MiddlePart.SLDPRT` / `Optical Ring-MiddlePart.STEP` | Optical ring/baffle native model and neutral export |
| `Probe Extension.SLDPRT` / `Probe Extension.STEP` | Probe extension native model and neutral export |

## Proposed device features

- Detachable optical probe intended to support replacement and servicing.
- Separate display and physical keypad, reducing dependence on touch input.
- Modular probe and controller housings.
- Rechargeable operation and local signal processing.
- Planned measurement-quality checks, reference checks and repeatability logging.
- Investigation of pigmentation-related measurement variation.

These are design goals, not demonstrated advantages over commercial screening devices. A keypad does not compensate for a failed display.

## Run the dashboard

1. Download and extract the repository, or clone it.
2. Open `neox_dashboard.html` from the repository folder in a browser.
3. Use the calibration and prediction sections to inspect the synthetic-data demonstration.
4. For sensor readings, use the compatible ESP32 firmware described below.

Chart.js is loaded from an external CDN. Charts may require internet access or a cached copy of that library. The exported PNG can be viewed without Chart.js.

## Initial ESP32 firmware

### Software dependencies

- Arduino IDE with ESP32 board support.
- Adafruit TCS34725 library and its required dependencies.
- A board selection matching the actual ESP32 development board.

Place `NeoX_TCS34725_WiFi.ino` in a folder named `NeoX_TCS34725_WiFi`, or allow Arduino IDE to create that sketch folder when opening the file.

### Connections defined in the sketch

| Signal | ESP32 connection |
|---|---|
| TCS34725 supply | 3.3 V and GND, subject to the breakout specification |
| TCS34725 SDA | GPIO 21 |
| TCS34725 SCL | GPIO 22 |
| External red LED control | GPIO 26 |
| External green LED control | GPIO 25 |
| External blue LED control | GPIO 27 |
| Breakout illumination LED control | GPIO 33, driven LOW by the sketch |

The sketch comments specify a 220-ohm series resistor for each external LED. Confirm LED current and GPIO limits for the actual parts. The breakout illumination-control pin and polarity must also be checked against the specific board.

### Connect the dashboard

1. Compile and upload the sketch to the ESP32.
2. Open Serial Monitor at **115200 baud** and check sensor initialization.
3. Connect the computer to Wi-Fi network **`NeoX_Sensor`**. The demonstration password is defined in the sketch; change it before shared use.
4. Open `http://192.168.4.1/data` to check the JSON response.
5. Open the dashboard and select **Take reading**.

The firmware continuously cycles through a dark measurement and RGB illumination. The endpoint returns the latest available result; a dashboard request does not trigger a new measurement cycle.

The JSON includes `blue`, `melanin`, `green`, `dB`, `dG`, `dRr`, `dGr` and `amb`. The `blue` and `melanin` fields are optical ratios, not direct biochemical measurements. The server enables cross-origin requests, but browser security rules may still restrict local-network access. In particular, an HTTPS-hosted dashboard may block the ESP32's HTTP endpoint.

### Known firmware limitation

In the included snapshot, a low-signal cycle after a successful cycle does not clear `latest.valid`. Consequently, `/data` can continue returning an older result as though it were current. Invalid-result handling, measurement age and saturation checks should be implemented and tested before relying on live readings.

## Synthetic calibration and regression

The included dataset contains **1,000 synthetic rows**, not clinical measurements or independently validated sensor observations.

- Features: `S_Blue` and `S_Melanin`.
- Target: `Bili_Equiv_mg_dL`, a synthetic demonstration label.
- Model: ordinary least squares linear regression.
- Split: 800 training rows and 200 held-out test rows.
- Split stratification: dataset `Skin_Tone` labels; random seed 42.

Saved model equation:

```text
Bili_equiv = 43.771318833
             - 43.113747128 * S_Blue
             - 7.232630861 * S_Melanin
```

| Saved metric | Training | Held-out test |
|---|---:|---:|
| R² | 0.995481 | 0.994845 |
| RMSE, synthetic target units | 0.395264 | 0.407572 |
| MAE, synthetic target units | 0.316305 | 0.327171 |

These are saved synthetic-data metrics, not verified clinical accuracy. Synthetic skin-tone groups do not establish performance across real skin tones. Applying these coefficients to live optical ratios does not establish a valid bilirubin measurement.

The source dataset's `S_Corrected` uses a different calculation from the fitted model correction. The exported calibration dataset preserves the source value as `Source_S_Corrected` and separately includes `Model_S_Corrected`.

### Reproduce training

From the repository folder:

```bash
python -m pip install numpy scikit-learn matplotlib
python train_ml_model.py
```

The script overwrites `neox_model.json`, `neox_calibration_dataset.csv` and `neox_calibration_curve_1000.png`. It does not change the source dataset or automatically update coefficients embedded in `neox_dashboard.html`. If training changes, synchronize the dashboard coefficients explicitly. Dependency versions are not pinned in this snapshot.

## CAD and schematic

Keep `Assem1.SLDASM` and all three `.SLDPRT` files together when opening the assembly. If SolidWorks reports missing references, locate the supplied part files. STEP files provide neutral geometry exports; they do not preserve the full native feature history.

The schematic identifies an **STM32F401CCUx** and a connector labelled **MAX86916 evaluation board**, together with an OLED, microSD module, push button, LEDs and power components. It is a proposed design, not a verified assembly instruction.

The schematic and latest device concept still need alignment: the proposed BOM uses a Nucleo development board, and the concept includes a keypad. Board selection, power rails, pin mapping, cable communication and enclosure dimensions must be reconciled before fabrication. The schematic does not establish completed STM32/MAX86916 integration.

## Phantom research and validation

Gelatin-based phantoms with controlled colorant concentrations can support investigations of optical response and repeatability. Such colorants are not equivalent to bilirubin or melanin, and simplified phantoms do not reproduce every property of newborn skin. This repository's synthetic dataset must not be described as measured phantom or patient data.

Future work includes controlled physical measurements, reference comparisons, probe replacement checks, signal-quality handling and evaluation across varied phantom compositions. Clinical performance would require a separate, appropriately approved validation programme.

## Verification and progress records

The presence of native CAD, schematic and firmware files documents engineering work; it does not establish that the complete device has been assembled, tested or clinically validated. Firmware compilation, hardware operation, CAD assembly integrity and schematic electrical checks should be recorded with the actual tool versions and results when performed.

Commit genuine updates as work progresses. GitHub commit history records repository changes; timestamps in a downloaded ZIP alone do not prove original creation dates.
