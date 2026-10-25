/*
  NeoX firmware - ESP32 + TCS34725 + R/G/B LEDs
  Creates WiFi hotspot NeoX_Sensor (password neox2024)
  Serves live JSON at http://192.168.4.1/data for neox_dashboard.html

  Wiring:
    LED_R GPIO 26, LED_G GPIO 25, LED_B GPIO 27 (each via 220 ohm to GND)
    TCS34725: 3.3V, GND, SDA=21, SCL=22, LED=33
*/
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_TCS34725.h>

const char* AP_SSID = "NeoX_Sensor";
const char* AP_PASS = "neox2024";

const int LED_R = 26, LED_G = 25, LED_B = 27, SENSOR_LED = 33;
const int N = 5;  // readings averaged per LED step

Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_154MS, TCS34725_GAIN_4X);
WebServer server(80);

// Latest result, served instantly on every /data request
struct Result {
  float sBlue = 0, sMelanin = 0, sGreen = 0;
  float dB = 0, dG = 0, dRr = 0, dGr = 0, amb = 0;
  bool valid = false;
  unsigned long cycle = 0;
} latest;

// Wait while still answering web requests (keeps the dashboard responsive)
void waitMs(unsigned long ms) {
  unsigned long t = millis();
  while (millis() - t < ms) {
    server.handleClient();
    delay(2);
  }
}

void allOff() {
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_G, LOW);
  digitalWrite(LED_B, LOW);
}

// pin = -1 means all LEDs off (dark reading)
void measure(int pin, float &r, float &g, float &b, float &c) {
  allOff();
  if (pin >= 0) digitalWrite(pin, HIGH);
  waitMs(300);
  uint16_t rr, gg, bb, cc;
  tcs.getRawData(&rr, &gg, &bb, &cc);  // discard first
  float sr = 0, sg = 0, sb = 0, sc = 0;
  for (int i = 0; i < N; i++) {
    waitMs(160);
    tcs.getRawData(&rr, &gg, &bb, &cc);
    sr += rr; sg += gg; sb += bb; sc += cc;
  }
  r = sr / N; g = sg / N; b = sb / N; c = sc / N;
  allOff();
}

void runCycle() {
  float dr, dg, db, dc;      // dark
  float r1, g1, b1, c1;      // blue LED on
  float r2, g2, b2, c2;      // green LED on
  float r3, g3, b3, c3;      // red LED on

  measure(-1,    dr, dg, db, dc);
  measure(LED_B, r1, g1, b1, c1);
  measure(LED_G, r2, g2, b2, c2);
  measure(LED_R, r3, g3, b3, c3);

  float dB  = b1 - db;   // blue channel under blue LED
  float dG  = g2 - dg;   // green channel under green LED
  float dRr = r3 - dr;   // red channel under red LED
  float dGr = g3 - dg;   // green channel under red LED

  if (dB > 1 && dG > 1 && dGr > 1) {
    latest.dB = dB; latest.dG = dG; latest.dRr = dRr; latest.dGr = dGr;
    latest.amb = dc;
    latest.sBlue = dB / dG;
    latest.sMelanin = dRr / dGr;
    latest.sGreen = dG / dGr;
    latest.valid = true;
    latest.cycle++;
    Serial.printf("cycle %lu  s_blue=%.4f  s_melanin=%.4f  dB=%.0f dG=%.0f dRr=%.0f dGr=%.0f amb=%.0f\n",
                  latest.cycle, latest.sBlue, latest.sMelanin, dB, dG, dRr, dGr, dc);
  } else {
    Serial.println("Signal too low - move probe closer to the surface");
  }
}

void handleData() {
  server.sendHeader("Access-Control-Allow-Origin", "*");  // lets a dashboard opened from a file fetch this
  if (!latest.valid) {
    server.send(503, "application/json", "{\"error\":\"no valid reading yet\"}");
    return;
  }
  char buf[256];
  snprintf(buf, sizeof(buf),
           "{\"blue\":%.4f,\"melanin\":%.4f,\"green\":%.4f,"
           "\"dB\":%.0f,\"dG\":%.0f,\"dRr\":%.0f,\"dGr\":%.0f,\"amb\":%.0f}",
           latest.sBlue, latest.sMelanin, latest.sGreen,
           latest.dB, latest.dG, latest.dRr, latest.dGr, latest.amb);
  server.send(200, "application/json", buf);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_R, OUTPUT); pinMode(LED_G, OUTPUT); pinMode(LED_B, OUTPUT);
  pinMode(SENSOR_LED, OUTPUT);
  digitalWrite(SENSOR_LED, LOW);
  allOff();

  Wire.begin(21, 22);
  if (!tcs.begin(TCS34725_ADDRESS, &Wire)) {
    Serial.println("TCS34725 not found");
    while (1) delay(1000);
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  Serial.print("Hotspot: "); Serial.println(AP_SSID);
  Serial.print("IP: "); Serial.println(WiFi.softAPIP());  // should be 192.168.4.1

  server.on("/data", HTTP_GET, handleData);
  server.begin();
}

void loop() {
  runCycle();          // ~5 s per full measurement; web server stays live during it
  server.handleClient();
}