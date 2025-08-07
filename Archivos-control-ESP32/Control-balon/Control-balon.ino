#include <WiFi.h>
#include <PubSubClient.h>

// Constantes del sistema
#define UMBRAL_PRESION     3600
#define INTENTOS_CONEXION  6
#define CANT_SENSORES      6
#define SSID_WIFI          "sensplay"
#define CLAVE_WIFI         "PC_2025grupo1"
#define BROKER_MQTT        "192.168.0.101"

// Pines de sensores
const uint8_t pinesFSR[CANT_SENSORES] = {34, 35, 32, 33, 25, 26};

// Estados
bool presionAnterior[CANT_SENSORES] = {false};
bool modoActivo = false;
bool estadoPrevio = false;

WiFiClient clienteWiFi;
PubSubClient clienteMQTT(clienteWiFi);

// Procesar mensajes entrantes
void callback(char* topic, byte* payload, unsigned int length) {
  String mensaje;
  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }
  mensaje.trim();
  if (String(topic) == "/rasp/balon/estado") {
    if (mensaje == "on") modoActivo = true;
    else if (mensaje == "off") modoActivo = false;
  }
}

// Conexión WiFi
void conectarWiFi() {
  Serial.print("WiFi");
  WiFi.begin(SSID_WIFI, CLAVE_WIFI);
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < INTENTOS_CONEXION) {
    delay(1000); Serial.print(".");
    intentos++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Conectado");
  } else {
    Serial.println(" Error WiFi, reiniciando...");
    delay(1000); ESP.restart();
  }
}

// Conexión MQTT
void conectarMQTT() {
  Serial.print("MQTT");
  int intentos = 0;
  while (!clienteMQTT.connected() && intentos < INTENTOS_CONEXION) {
    if (clienteMQTT.connect("ESP32Balon")) {
      clienteMQTT.publish("/rasp/balon/estado", "conectado", false);
      clienteMQTT.subscribe("/rasp/balon/estado");
      Serial.println(" Conectado");
      Serial.println("Estado (off), Esperando inicio...");
      return;
    }
    delay(500); Serial.print(".");
    intentos++;
  }
  Serial.println(" Error MQTT, reiniciando...");
  delay(1000); ESP.restart();
}

// Setup inicial
void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < CANT_SENSORES; i++) {
    pinMode(pinesFSR[i], INPUT);
    analogSetPinAttenuation(pinesFSR[i], ADC_11db);
  }
  conectarWiFi();
  clienteMQTT.setServer(BROKER_MQTT, 1883);
  clienteMQTT.setCallback(callback);
  conectarMQTT();
}

// Bucle principal
void loop() {
  if (WiFi.status() != WL_CONNECTED) conectarWiFi();
  if (!clienteMQTT.connected()) conectarMQTT();
  clienteMQTT.loop();

  if (modoActivo != estadoPrevio) {
    if (modoActivo) Serial.println("Estado (on), Enviando lecturas...");
    else Serial.println("Estado (off), Esperando inicio...");
    estadoPrevio = modoActivo;
  }

  if (!modoActivo) {
    delay(200);
    return;
  }

  for (uint8_t i = 0; i < CANT_SENSORES; i++) {
    uint16_t lectura = analogRead(pinesFSR[i]);
    bool presionado = lectura > UMBRAL_PRESION;
    
    if (presionado && !presionAnterior[i]) {
      String mensaje = "S" + String(i + 1);
      clienteMQTT.publish("/rasp/balon/sensores", mensaje.c_str());
      clienteMQTT.publish("/rasp/rgb/animacion/conteo", "1"); // para tira led
      delay(180); // tiempo entre detecciones
    }

    presionAnterior[i] = presionado;
  }

  delay(50);
}
