#!/usr/bin/env python3
"""
Скрипт для загрузки тайлов изображений и их объединения в одну большую картинку.
Загружает 9 тайлов (3x3 сетка) размером 1000x1000 пикселей каждый.
"""

import os
import time
from io import BytesIO
import requests
from PIL import Image
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL-адреса тайлов в виде сетки 3x3
TILE_URLS = [
    ["https://backend.wplace.live/files/s0/tiles/1506/631.png", 
     "https://backend.wplace.live/files/s0/tiles/1507/631.png", 
     "https://backend.wplace.live/files/s0/tiles/1508/631.png"],
    ["https://backend.wplace.live/files/s0/tiles/1506/632.png", 
     "https://backend.wplace.live/files/s0/tiles/1507/632.png", 
     "https://backend.wplace.live/files/s0/tiles/1508/632.png"],
    ["https://backend.wplace.live/files/s0/tiles/1506/633.png", 
     "https://backend.wplace.live/files/s0/tiles/1507/633.png", 
     "https://backend.wplace.live/files/s0/tiles/1508/633.png"]
]

# Размеры
TILE_SIZE = 1000  # Размер каждого тайла (1000x1000)
GRID_SIZE = 3     # Размер сетки (3x3)
ORIGINAL_SIZE = TILE_SIZE * GRID_SIZE  # Оригинальный размер (3000x3000)
FINAL_SIZE = 9000  # Увеличенный размер для лучшей видимости пикселей
SCALE_FACTOR = FINAL_SIZE // ORIGINAL_SIZE  # Коэффициент масштабирования (3x)

def download_image(url, timeout=30, retries=5, backoff_seconds=1.5):
    """
    Загружает изображение по URL.
    
    Args:
        url (str): URL изображения
        timeout (int): Таймаут запроса в секундах
        retries (int): Количество попыток загрузки
        backoff_seconds (float): Базовая пауза между попытками
        
    Returns:
        PIL.Image: Загруженное изображение или None в случае ошибки
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Загружаю изображение (попытка {attempt}/{retries}): {url}")
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            # Читаем содержимое и открываем через BytesIO, чтобы не зависеть от открытого потока
            content = response.content
            image = Image.open(BytesIO(content))
            image.load()
            logger.info(f"Успешно загружено: {url}")
            return image
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(f"Ошибка при загрузке {url} (попытка {attempt}/{retries}): {e}")
        except Exception as e:
            last_error = e
            logger.warning(f"Ошибка при обработке изображения {url} (попытка {attempt}/{retries}): {e}")
        # Бэкофф между попытками, если не последняя
        if attempt < retries:
            sleep_seconds = backoff_seconds * attempt
            time.sleep(sleep_seconds)
    logger.error(f"Не удалось загрузить {url} после {retries} попыток: {last_error}")
    return None

def create_merged_image():
    """
    Создает объединенное изображение из всех тайлов.
    Дамп сохраняется только при 100% успешной загрузке всех тайлов.
    
    Returns:
        PIL.Image: Объединенное изображение или None в случае ошибки
    """
    # Создаем новое изображение с оригинальным размером 3000x3000 с прозрачным фоном
    merged_image = Image.new('RGBA', (ORIGINAL_SIZE, ORIGINAL_SIZE), color=(0, 0, 0, 0))
    
    failed_tiles = []
    successful_tiles = 0
    total_tiles = GRID_SIZE * GRID_SIZE
    
    logger.info(f"Начинаю загрузку {total_tiles} тайлов (сетка {GRID_SIZE}x{GRID_SIZE})")
    
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            url = TILE_URLS[row][col]
            logger.info(f"Загружаю тайл [{row+1},{col+1}] из {total_tiles}: {url}")
            tile = download_image(url)
            
            if tile is not None:
                # Убеждаемся, что размер тайла корректный
                if tile.size != (TILE_SIZE, TILE_SIZE):
                    logger.warning(f"Неожиданный размер тайла {url}: {tile.size}. Изменяю размер до {TILE_SIZE}x{TILE_SIZE}")
                    tile = tile.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
                
                # Конвертируем в RGBA если необходимо
                if tile.mode != 'RGBA':
                    tile = tile.convert('RGBA')
                
                # Вычисляем позицию для вставки
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                
                # Вставляем тайл в объединенное изображение с учетом альфа-канала
                merged_image.paste(tile, (x, y), tile)
                successful_tiles += 1
                logger.info(f"✅ Тайл [{row+1},{col+1}] успешно вставлен в позицию ({x}, {y}) - {successful_tiles}/{total_tiles}")
            else:
                failed_tiles.append(url)
                logger.error(f"❌ Не удалось загрузить тайл [{row+1},{col+1}]: {url}")
    
    # Проверяем результат загрузки
    if failed_tiles:
        logger.error(f"❌ ЗАГРУЗКА НЕУДАЧНА: {len(failed_tiles)} из {total_tiles} тайлов не загружены")
        logger.error("Дамп НЕ будет сохранен, так как нужны ВСЕ тайлы для корректного отображения")
        for i, url in enumerate(failed_tiles, 1):
            logger.error(f"  {i}. Неудачный тайл: {url}")
        return None
    
    # Все тайлы загружены успешно
    logger.info(f"✅ ЗАГРУЗКА УСПЕШНА: все {successful_tiles}/{total_tiles} тайлов загружены")
    logger.info("Создаю объединенный дамп...")

    # Увеличиваем изображение до 9000x9000 для лучшей видимости пикселей
    logger.info(f"Масштабирую изображение с {ORIGINAL_SIZE}x{ORIGINAL_SIZE} до {FINAL_SIZE}x{FINAL_SIZE} (коэффициент {SCALE_FACTOR}x)")
    scaled_image = merged_image.resize((FINAL_SIZE, FINAL_SIZE), Image.Resampling.NEAREST)
    
    return scaled_image

def save_image(image, output_dir="output"):
    """
    Сохраняет изображение с временной меткой в папку с датой.
    
    Args:
        image (PIL.Image): Изображение для сохранения
        output_dir (str): Директория для сохранения
        
    Returns:
        str: Путь к сохраненному файлу или None в случае ошибки
    """
    try:
        # Создаем директорию если её нет
        os.makedirs(output_dir, exist_ok=True)
        
        # Создаем папку с сегодняшней датой
        from datetime import timedelta, timezone
        TOMSK_TZ = timezone(timedelta(hours=7))
        today = datetime.now(TOMSK_TZ).strftime("%Y%m%d")
        today_folder = os.path.join(output_dir, today)
        os.makedirs(today_folder, exist_ok=True)
        
        # Генерируем имя файла с временной меткой
        timestamp = datetime.now(TOMSK_TZ).strftime("%Y%m%d_%H%M%S")
        filename = f"merged_tiles_{timestamp}.png"
        filepath = os.path.join(today_folder, filename)
        
        # Сохраняем изображение с прозрачностью в папку с датой
        image.save(filepath, "PNG", optimize=True, compress_level=9)
        logger.info(f"Изображение сохранено: {filepath}")
        
        return filepath
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {e}")
        return None

def main():
    """
    Основная функция скрипта.
    Дамп сохраняется только при 100% успешной загрузке всех тайлов.
    """
    logger.info("🚀 Начинаю процесс загрузки и объединения тайлов")
    logger.info("📋 Требование: дамп будет создан только при загрузке ВСЕХ 9 тайлов")
    
    # Создаем объединенное изображение
    merged_image = create_merged_image()
    
    if merged_image is not None:
        # Сохраняем результат
        logger.info("💾 Сохраняю объединенный дамп...")
        saved_path = save_image(merged_image)
        
        if saved_path:
            logger.info(f"✅ ПРОЦЕСС УСПЕШНО ЗАВЕРШЕН!")
            logger.info(f"📁 Дамп сохранен в: {saved_path}")
            logger.info(f"🔗 Latest версия: {os.path.join('output', 'latest.png')}")
            return True
        else:
            logger.error("❌ Не удалось сохранить объединенное изображение")
            return False
    else:
        logger.error("❌ Не удалось создать объединенное изображение")
        logger.error("💡 Возможные причины:")
        logger.error("   - Не все тайлы доступны для загрузки")
        logger.error("   - Проблемы с сетью или сервером")
        logger.error("   - Неверные URL адреса тайлов")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)


