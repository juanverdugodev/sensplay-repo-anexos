// Librerías para control
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>
// Definición de constantes para control
#define PIN_GPIO           18
#define NUM_LEDS           50 // Si existen mas leds
#define LEDS_ACTIVAS       48
#define BRILLO_MAXIMO_REAL 10   // PWM máximo real (0–255) para brillo
// Credenciales y broker
const char* ssid       = "sensplay";
const char* password   = "PC_2025grupo1";
const char* brokerMQTT = "192.168.0.101";
WiFiClient    clienteWiFi;
PubSubClient  clienteMQTT(clienteWiFi);
Adafruit_NeoPixel tira(NUM_LEDS, PIN_GPIO, NEO_GRB + NEO_KHZ800);
// Estado global
typedef enum {APAGADO, ENCENDIDA, ARCOIRIS, COLORESMOD, CONTEO} Estado;
Estado modoActual = APAGADO;
Estado modoAnterior = APAGADO;
uint8_t porcentajeBrillo = 100;
uint16_t indiceArcoiris = 0;
uint8_t rMod=0, gMod=0, bMod=0;
bool nuevaAnimacionConteo = false;
// Variable global para contar LEDs encendidos en animacionConteo
uint8_t ledsEncendidosInterno = 0;
uint8_t brilloPorcentaje(uint8_t pct) {
  if (pct > 100) pct = 100;
  return map(pct, 0, 100, 0, BRILLO_MAXIMO_REAL);
}
void apagarTira() {
  tira.clear();
  tira.show();
}
void encendida() {
  tira.setBrightness(brilloPorcentaje(porcentajeBrillo));
  for (int i = 0; i < LEDS_ACTIVAS; i++) {
    tira.setPixelColor(i, tira.Color(28, 75, 141));
  }
  tira.show();
}
void animacionParpadeo(uint32_t color) {
  for (int p = 0; p < 2; p++) {
    tira.setBrightness(BRILLO_MAXIMO_REAL);
    for (int i = 0; i < LEDS_ACTIVAS; i++) tira.setPixelColor(i, color);
    tira.show(); delay(300);
    apagarTira(); delay(100);
  }
}
uint32_t ruedaColor(byte pos) {
  pos = 255 - pos;
  if (pos < 85) return tira.Color(255 - pos * 3, 0, pos * 3);
  if (pos < 170) { pos -= 85; return tira.Color(0, pos * 3, 255 - pos * 3); }
  pos -= 170;
  return tira.Color(pos * 3, 255 - pos * 3, 0);
}
void modoArcoiris() {
  tira.setBrightness(brilloPorcentaje(porcentajeBrillo));
  for (uint16_t i = 0; i < LEDS_ACTIVAS; i++) {
    tira.setPixelColor(i, ruedaColor((i * 256 / LEDS_ACTIVAS + indiceArcoiris) & 255));
  }
  tira.show();
  delay(20);
  indiceArcoiris = (indiceArcoiris + 1) % 256;
}
void modoColoresMod() {
  tira.setBrightness(brilloPorcentaje(porcentajeBrillo));
  for (int i = 0; i < LEDS_ACTIVAS; i++) {
    tira.setPixelColor(i, tira.Color(rMod, gMod, bMod));
  }
  tira.show();
}
void animacionConteo() {
  tira.setBrightness(brilloPorcentaje(porcentajeBrillo));
  // Encender LEDs acumulativamente
  for (uint8_t i = 0; i <= ledsEncendidosInterno && i < LEDS_ACTIVAS; i++) {
    tira.setPixelColor(i, tira.Color(28, 75, 141));
  }
  tira.show();
  ledsEncendidosInterno++;
  // Al llegar al máximo, hacemos parpadeo y reiniciamos
  if (ledsEncendidosInterno >= LEDS_ACTIVAS) {
    animacionParpadeo(tira.Color(28, 75, 141));
    apagarTira();
    ledsEncendidosInterno = 0;
  }
  nuevaAnimacionConteo = false;
}
void conectarWiFi() {
  Serial.print("Conectando WiFi");
  WiFi.begin(ssid, password);
  int intentos=0;
  while (WiFi.status()!=WL_CONNECTED && intentos<6) {
    delay(1000); Serial.print(".");
    intentos++;
  }
  if (WiFi.status()==WL_CONNECTED)
    Serial.println("\nWiFi OK, IP:"+WiFi.localIP().toString());
  else {
    Serial.println("\nError WiFi"); 
    animacionParpadeo(tira.Color(255,0,0));
    delay(1000);
    ESP.restart();
  }
}
void conectarMQTT() {
  Serial.print("Conectando MQTT");
  int intentos=0;
  while (!clienteMQTT.connected() && intentos<3) {
    if (clienteMQTT.connect("ESP32Client")) {
      clienteMQTT.subscribe("/rasp/rgb/brillo");
      clienteMQTT.subscribe("/rasp/rgb/animacion");
      clienteMQTT.subscribe("/rasp/rgb/animacion/coloresmod");
      clienteMQTT.subscribe("/rasp/rgb/estado");
      clienteMQTT.subscribe("/rasp/rgb/animacion/conteo");
      clienteMQTT.publish("/rasp/rgb/estado","conectado",false);
      animacionParpadeo(tira.Color(28,75,141));
      delay(1000);
      encendida();
      modoActual = ENCENDIDA;
      return;
    }
    delay(500); Serial.print(".");
    intentos++;
  }
  Serial.println("\nFallo MQTT");
  modoActual = APAGADO;
  animacionParpadeo(tira.Color(255,150,0));
}
void mensajeRecibido(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i=0; i<length; i++) 
    msg += (char)payload[i];
  msg.trim();

  if (String(topic)=="/rasp/rgb/brillo") {
    porcentajeBrillo = constrain(msg.toInt(),0,100);
  }
  else if (String(topic)=="/rasp/rgb/animacion") {
    if (msg=="arcoiris") modoActual = ARCOIRIS;
  }
  else if (String(topic)=="/rasp/rgb/animacion/coloresmod") {
    msg.trim(); msg.replace(" ","");
    char buf[32]; msg.toCharArray(buf,sizeof(buf));
    int r,g,b;
    if (sscanf(buf,"rgb(%d,%d,%d)",&r,&g,&b)==3) {
      rMod = constrain(r,0,255);
      gMod = constrain(g,0,255);
      bMod = constrain(b,0,255);
      modoActual = COLORESMOD;
    }
  }
  else if (String(topic)=="/rasp/rgb/estado") {
    if (msg=="on") modoActual = ENCENDIDA;
    else if (msg=="off") { modoActual = APAGADO; apagarTira(); }
  }
  else if (String(topic)=="/rasp/rgb/animacion/conteo") {
    if (msg=="1") {
      nuevaAnimacionConteo = true;
      modoActual = CONTEO;
    }
  }
}
void setup() {
  Serial.begin(115200);
  pinMode(PIN_GPIO,OUTPUT);
  digitalWrite(PIN_GPIO,LOW);
  tira.begin();
  tira.setBrightness(brilloPorcentaje(100));
  apagarTira();
  conectarWiFi();
  clienteMQTT.setServer(brokerMQTT,1883);
  clienteMQTT.setCallback(mensajeRecibido);
  conectarMQTT();
}
void loop() {
  if (WiFi.status()!=WL_CONNECTED) conectarWiFi();
  if (!clienteMQTT.connected()) conectarMQTT();
  clienteMQTT.loop();
  if (modoActual != modoAnterior) {
    apagarTira();
    ledsEncendidosInterno = (modoActual==CONTEO) ? ledsEncendidosInterno : 0;
    modoAnterior = modoActual;
  }
  if (modoActual == CONTEO) {
    tira.setBrightness(brilloPorcentaje(porcentajeBrillo));
    for (uint8_t i = 0; i < ledsEncendidosInterno && i < LEDS_ACTIVAS; i++) {
      tira.setPixelColor(i, tira.Color(28, 75, 141));
    }
    tira.show();
    if (nuevaAnimacionConteo) {
      animacionConteo();
    }
    return;
  }
  switch(modoActual) {
    case ARCOIRIS:    modoArcoiris();    break;
    case COLORESMOD:  modoColoresMod();  break;
    case ENCENDIDA:   encendida();       break;
    default:          delay(100);        break;
  }
}
