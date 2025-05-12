import os
import telegram
from openai import OpenAI
# Импортируем os для работы с файлами, уже есть

# --- Настройки API и канала ---
openai_api_key = os.getenv("OPENAI_API_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = "@dailyzendose" # Убедитесь, что это корректное @имя_канала или ID

client = OpenAI(api_key=openai_api_key)
bot = telegram.Bot(token=telegram_token)

# --- Настройки для Песни дня ---
SONGS_FILE = 'youtube_songs.txt' # Имя файла со списком песен
INDEX_FILE = 'current_song_index.txt' # Имя файла для хранения текущего индекса

# --- Вспомогательные функции для работы с файлами песен и индекса ---
def read_song_list(filename):
    """Читает список URL из файла, игнорируя пустые строки и комментарии."""
    songs = []
    print(f"Попытка чтения списка песен из файла: {filename}")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Игнорируем пустые строки и строки, начинающиеся с # (для комментариев)
                if line and not line.startswith('#'):
                    songs.append(line)
        print(f"Успешно прочитано {len(songs)} песен из '{filename}'.")
    except FileNotFoundError:
        print(f"Ошибка: Файл со списком песен '{filename}' не найден.")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла песен '{filename}': {e}")
        return []
    return songs

def read_current_index(filename):
    """Читает текущий индекс песни из файла."""
    print(f"Попытка чтения текущего индекса из файла: {filename}")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                index = int(content)
                print(f"Успешно прочитан индекс {index} из файла '{filename}'.")
                return index
            else:
                print(f"Файл индекса '{filename}' пуст.")
                return -1 # Вернем -1, если файл пуст, чтобы начать с 0
    except FileNotFoundError:
        print(f"Файл индекса '{filename}' не найден. Начнем с 0.")
        return -1 # Вернем -1, если файл не найден, чтобы начать с 0
    except ValueError:
        print(f"Предупреждение: Файл индекса '{filename}' содержит нечисловые данные. Начнем с 0.")
        return -1
    except Exception as e:
        print(f"Ошибка при чтении файла индекса '{filename}': {e}")
        return -1


def write_current_index(filename, index):
    """Записывает текущий индекс песни в файл."""
    print(f"Попытка записи индекса {index} в файл: {filename}")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(str(index))
        print(f"Индекс {index} успешно записан в файл '{filename}'.")
    except Exception as e:
        print(f"Ошибка записи файла индекса '{filename}': {e}")

# --- Основной код бота ---
print("Начало выполнения скрипта.")

# 1. Жёсткий промпт для цитаты
prompt = (
    "Сгенерируй одну мудрую цитату дня от известного человека, писателя, философа, героя книги, фильма и т.д. Важно, чтоб цитата была позитивной, вдохновляющей, мудрой и/или с юмором. "
    "Сначала напиши её на английском языке, затем переведи на русский. "
    "Строго в следующем формате:\n\n"
    "\"Английская цитата\" — Автор\n\"Русская цитата\" — Автор"
)
print("Запрос цитаты у GPT-4o...")
try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    # 2. Разбор цитаты
    text = response.choices[0].message.content.strip()
    lines = [line for line in text.split("\n") if line.strip()]
    english = lines[0].strip('"') if len(lines) >= 1 else ""
    russian = lines[1].strip('"') if len(lines) >= 2 else ""
    print("Цитата сгенерирована и разобрана.")
    # 3. Финальное сообщение для цитаты
    quote_text = f"Quote of the day:\n\n{english}\n\nЦитата дня:\n\n{russian}" if english and russian else english or text
    print(f"Финальный текст цитаты готов:\n---\n{quote_text}\n---")

    # 4. Извлечение темы для изображения
    print("Извлечение темы цитаты для изображения...")
    theme_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Вот цитата:\n\n{english}\n\n"
                    "Определи её главную тему одним словом или фразой (на английском)."
                )
            }
        ]
    )
    theme = theme_response.choices[0].message.content.strip()
    print(f"Тема цитаты определена: {theme}")

    # 5. Генерация изображения
    print("Запрос генерации изображения у DALL-E 3...")
    image = client.images.generate(
        model="dall-e-3",
        prompt=f"Symbolic concept of {theme}, artistic rendering, elegant, high detail, blend of vintage and cybernetic aesthetics",
        n=1,
        size="1024x1024"
    )
    image_url = image.data[0].url
    print(f"Изображение сгенерировано. URL: {image_url}")

    # 6. Отправка первого поста (Фото + Цитата)
    print("Попытка отправки первого поста (Фото + Цитата) в Telegram...")
    bot.send_photo(chat_id=chat_id, photo=image_url, caption=quote_text)
    print("Первый пост (Фото + Цитата) отправлен успешно.")

except Exception as e:
    print(f"Критическая ошибка на шаге генерации/отправки цитаты/изображения: {e}")
    # Если первый пост не удалось отправить, возможно, нет смысла отправлять второй.
    # Можете добавить здесь выход из скрипта или уведомление.


# --- 7. Подготовка и отправка второго поста (Песня дня) ---

print("\n--- Начинаем подготовку к отправке 'Песни дня' ---")

youtube_songs = read_song_list(SONGS_FILE)

if not youtube_songs:
    print(f"Не могу отправить 'Песню дня': список песен пуст или файл '{SONGS_FILE}' не найден или содержит ошибки.")
    # Опционально: отправить сообщение об ошибке в канал
    # try:
    #     bot.send_message(chat_id=chat_id, text="Не удалось загрузить список песен дня.")
    # except Exception as e_msg:
    #     print(f"Ошибка при отправке сообщения об ошибке списка песен: {e_msg}")

else:
    # Список песен загружен, приступаем к выбору следующей песни
    current_index = read_current_index(INDEX_FILE)
    # read_current_index уже печатает статус

    # Определяем индекс следующей песни
    # Если read_current_index вернул -1 (файл не найден или пуст/некорректен), начнем с индекса 0
    # Убедимся, что current_index не None (если read_current_index поймал другую ошибку)
    next_index = current_index + 1 if current_index is not None and current_index != -1 else 0

    # Реализация цикла: если next_index равен или больше количества песен, сбрасываем на 0
    if next_index >= len(youtube_songs):
        next_index = 0
        print("Достигнут конец списка песен, сброс индекса на 0.")

    print(f"Рассчитан индекс песни для следующей отправки: {next_index}")

    # Получаем URL песни по рассчитанному индексу
    try:
        song_url = youtube_songs[next_index]
        print(f"URL песни для отправки: {song_url}")

        # Отправляем сообщение с "Песней дня"
        print("Попытка отправки сообщения 'Песня дня' в Telegram...")
        bot.send_message(
            chat_id=chat_id,
            text=f"Song Of The Day - Песня Дня 🎧🌟\n\n{song_url}" # <-- Ваш новый текст
        )
        print("'Песня дня' сообщение отправлено успешно.")

        # Важно: Сохраняем НОВЫЙ индекс ПОСЛЕ успешной отправки сообщения в Telegram
        print(f"Попытка записи нового индекса {next_index} в файл '{INDEX_FILE}'...")
        write_current_index(INDEX_FILE, next_index)
        print(f"Новый индекс {next_index} успешно записан в файл '{INDEX_FILE}'.")

    except IndexError:
         print(f"Ошибка: Индекс песни {next_index} вне диапазона ({len(youtube_songs)} песен). Проверьте файл '{SONGS_FILE}'.")
         # Опционально: отправить сообщение об ошибке в канал
         # try:
         #     bot.send_message(chat_id=chat_id, text="Ошибка выбора песни дня. Проверьте список песен.")
         # except Exception as e_msg:
         #      print(f"Ошибка при отправке сообщения об ошибке выбора песни: {e_msg}")
    except Exception as e:
        # Эта ошибка отлавливает проблемы при отправке сообщения или при записи файла индекса
        print(f"ПРОИЗОШЛА ОШИБКА ПРИ ОТПРАВКЕ ПЕСНИ ДНЯ ИЛИ ЗАПИСИ ИНДЕКСА: {e}")
        print(f"Индекс песни ({next_index}) НЕ БЫЛ обновлен в файле '{INDEX_FILE}'.")
        # Если отправка не удалась, мы НЕ обновляем файл индекса,
        # чтобы бот попробовал отправить ту же песню в следующий раз.

print("\nВыполнение скрипта завершено.")

# Конец скрипта
