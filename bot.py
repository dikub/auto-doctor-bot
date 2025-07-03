from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import requests

USER = {
    "snum": "0000000000",  # Личный номер
    "spin": "0000",  # Пин-код
    "doctor_name": "Зубович Ю.П.",
    "wait_time": 15
}

# === ДАННЫЕ ДЛЯ TELEGRAM ===
TELEGRAM_BOT_TOKEN = '0000000000000000000000000000000000000000'
TELEGRAM_CHAT_ID = '0000000000000'


def notify_telegram_message(message_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message_text}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("📬 Уведомление отправлено в Telegram")
        else:
            print(f"⚠️ Ошибка Telegram: {response.text}")
    except Exception as e:
        print(f"⚠️ Telegram-сбой: {e}")


BASE_URL = "https://tutmed.by/cgi-bin/is11_60?sfl_=313&nofull=1"

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def go_to_main():
    driver.get(BASE_URL)


successful_booking = False

while not successful_booking:
    try:
        go_to_main()
        print("🔎 Поиск врача...")
        doctor_button = WebDriverWait(driver, USER['wait_time']).until(
            EC.element_to_be_clickable((By.XPATH, f"//td[contains(text(), '{USER['doctor_name']}')]"))
        )
        doctor_button.click()
        print(f"✅ Найден и выбран врач: {USER['doctor_name']}")

        WebDriverWait(driver, USER['wait_time']).until(
            EC.presence_of_element_located((By.NAME, "f11_61_0"))
        )

        snum_input = driver.find_element(By.NAME, "snum_")
        spin_input = driver.find_element(By.NAME, "spin_")
        snum_input.clear()
        spin_input.clear()
        snum_input.send_keys(USER["snum"])
        spin_input.send_keys(USER["spin"])

        print("🗓 Поиск доступных дат...")
        time.sleep(1)

        free_time_buttons = driver.find_elements(By.XPATH, "//td[@onclick and contains(@onclick, 'js_11_61_1')]")
        if not free_time_buttons:
            print("❌ Нет доступных дат, пробуем снова через 5 сек...")
            time.sleep(5)
            continue
        else:
            notify_telegram_message(f"📅 Найдена доступная дата записи к врачу {USER['doctor_name']}.")

            for date_button in free_time_buttons:
                try:
                    onclick_value = date_button.get_attribute("onclick")
                    match = re.search(r"js_11_61_1\((\d+),", onclick_value)
                    menu_number = match.group(1) if match else None
                    if not menu_number:
                        print(f"⚠️ Не удалось определить дату из: {onclick_value}")
                        continue

                    menu_id = f"menu{menu_number}"
                    date_button.click()
                    print("✅ Дата выбрана, ожидаем меню с временем...")

                    WebDriverWait(driver, USER['wait_time']).until(
                        EC.visibility_of_element_located((By.ID, menu_id))
                    )
                    menu_div = driver.find_element(By.ID, menu_id)

                    iframe = menu_div.find_element(By.TAG_NAME, "iframe")
                    WebDriverWait(driver, USER['wait_time']).until(
                        EC.frame_to_be_available_and_switch_to_it(iframe)
                    )

                    print("🕒 Ищем доступное время...")

                    time_cells = driver.find_elements(By.XPATH, "//td[contains(@onclick, 'js_11_62_1')]")
                    if not time_cells:
                        print("❌ Нет доступного времени в iframe")
                        driver.switch_to.default_content()
                        continue

                    time_cells[0].click()
                    print("✅ Время выбрано, отправляем запись")

                    try:
                        WebDriverWait(driver, 5).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        print(f"🔔 Подтверждение: {alert.text}")
                        alert.accept()
                        print("✅ Alert принят, продолжаем...")
                    except:
                        print("⚠️ Alert не появился")

                    driver.switch_to.default_content()
                    time.sleep(5)
                    page_source = driver.page_source.lower()
                    if "запись завершена" in page_source or "успешно" in page_source:
                        print("🚀 Запись успешно завершена!")
                        notify_telegram_message(f"✅ Вы успешно записаны к врачу {USER['doctor_name']}")
                        successful_booking = True  # <<< выход из внешнего while
                        break  # <<< выход из for после первой записи
                    else:
                        print("⚠️ Запись отправлена, но подтверждение не найдено.")
                except Exception as e:
                    print(f"⚠️ Ошибка при обработке даты: {e}")

            if not successful_booking:
                print("❌ Не удалось записаться — ни на одну дату не было свободного времени. Ждём 5 сек...")
                time.sleep(5)

    except TimeoutException:
        print("❌ Врач не найден или сайт недоступен, повтор через 5 сек...")
        time.sleep(5)
    except NoSuchElementException as e:
        print(f"❌ Ошибка поиска элемента: {e}, повтор через 5 сек...")
        time.sleep(5)

input("Нажмите Enter для завершения и закрытия браузера...")
driver.quit()

