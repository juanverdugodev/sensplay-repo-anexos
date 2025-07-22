import pyautogui
import time

try:
    print("Autoclick iniciado. Mueve el mouse a la esquina superior izquierda para detener.")
    time.sleep(5)

    while True:
        pyautogui.click()
        time.sleep(0.1)  # Intervalo entre clics
except KeyboardInterrupt:
    print("Autoclick detenido manualmente.")
