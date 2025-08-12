#!/usr/bin/env python3
"""
Скрипт для загрузки тайлов изображений и их объединения в одну большую картинку.
Загружает 9 тайлов (3x3 сетка) размером 1000x1000 пикселей каждый.
"""

import os
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
FINAL_SIZE = TILE_SIZE * GRID_SIZE  # Итоговый размер (3000x3000)

def download_image(url, timeout=30):
    """
    Загружает изображение по URL.
    
    Args:
        url (str): URL изображения
        timeout (int): Таймаут запроса в секундах
        
    Returns:
        PIL.Image: Загруженное изображение или None в случае ошибки
    """
    try:
        logger.info(f"Загружаю изображение: {url}")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        image = Image.open(requests.get(url, stream=True).raw)
        logger.info(f"Успешно загружено: {url}")
        return image
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при загрузке {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения {url}: {e}")
        return None

def create_merged_image():
    """
    Создает объединенное изображение из всех тайлов.
    
    Returns:
        PIL.Image: Объединенное изображение или None в случае ошибки
    """
    # Создаем новое изображение с размером 3000x3000
    merged_image = Image.new('RGB', (FINAL_SIZE, FINAL_SIZE), color='white')
    
    failed_tiles = []
    
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            url = TILE_URLS[row][col]
            tile = download_image(url)
            
            if tile is not None:
                # Убеждаемся, что размер тайла корректный
                if tile.size != (TILE_SIZE, TILE_SIZE):
                    logger.warning(f"Неожиданный размер тайла {url}: {tile.size}. Изменяю размер до {TILE_SIZE}x{TILE_SIZE}")
                    tile = tile.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
                
                # Вычисляем позицию для вставки
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                
                # Вставляем тайл в объединенное изображение
                merged_image.paste(tile, (x, y))
                logger.info(f"Тайл вставлен в позицию ({x}, {y})")
            else:
                failed_tiles.append(url)
                logger.error(f"Не удалось загрузить тайл: {url}")
    
    if failed_tiles:
        logger.warning(f"Не удалось загрузить {len(failed_tiles)} тайлов из {GRID_SIZE * GRID_SIZE}")
        for url in failed_tiles:
            logger.warning(f"Неудачный тайл: {url}")
    
    return merged_image

def save_image(image, output_dir="output"):
    """
    Сохраняет изображение с временной меткой.
    
    Args:
        image (PIL.Image): Изображение для сохранения
        output_dir (str): Директория для сохранения
        
    Returns:
        str: Путь к сохраненному файлу или None в случае ошибки
    """
    try:
        # Создаем директорию если её нет
        os.makedirs(output_dir, exist_ok=True)
        
        # Генерируем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"merged_tiles_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        
        # Сохраняем изображение
        image.save(filepath, "PNG", optimize=True)
        logger.info(f"Изображение сохранено: {filepath}")
        
        # Также сохраняем как "latest.png" для удобства
        latest_path = os.path.join(output_dir, "latest.png")
        image.save(latest_path, "PNG", optimize=True)
        logger.info(f"Изображение также сохранено как: {latest_path}")
        
        return filepath
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {e}")
        return None

def main():
    """
    Основная функция скрипта.
    """
    logger.info("Начинаю процесс загрузки и объединения тайлов")
    
    # Создаем объединенное изображение
    merged_image = create_merged_image()
    
    if merged_image is not None:
        # Сохраняем результат
        saved_path = save_image(merged_image)
        
        if saved_path:
            logger.info(f"Процесс успешно завершен. Результат сохранен в: {saved_path}")
            return True
        else:
            logger.error("Не удалось сохранить объединенное изображение")
            return False
    else:
        logger.error("Не удалось создать объединенное изображение")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
