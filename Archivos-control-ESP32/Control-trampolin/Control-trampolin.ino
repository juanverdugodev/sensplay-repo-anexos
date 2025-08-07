#define TRIG_PIN 5
#define ECHO_PIN 18

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.println("Iniciando sensor ultrasónico HC-SR04...");
}

void loop() {
  // Enviar pulso de 10us
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Leer el pulso ECHO
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms de timeout

  if (duration == 0) {
    Serial.println("No se recibió señal del sensor (timeout)");
  } else {
    float distance = duration * 0.034 / 2;
    Serial.print("Distancia: ");
    Serial.print(distance);
    Serial.println(" cm");
  }

  delay(1000);
}
