#!/usr/bin/env python3
"""
Скрипт для загрузки и объединения тайлов с wplace.live по заданным координатам,
с последующей обрезкой и масштабированием.
"""

import os
import time
from io import BytesIO
import requests
from PIL import Image
from datetime import datetime
from zoneinfo import ZoneInfo
import concurrent.futures
import logging
from config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://backend.wplace.live/files/s0/tiles/{x}/{y}.png"

# --- ОСНОВНЫЕ ФУНКЦИИ ---

def download_image(url, timeout=30, retries=5, backoff_seconds=1.5):
    """
    Загружает изображение по URL с логикой повторных попыток.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Загружаю (попытка {attempt}/{retries}): {url}")
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            content = response.content
            image = Image.open(BytesIO(content))
            image.load()  # Убедимся, что данные изображения загружены
            logger.info(f"Успешно загружено: {url}")
            return image
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(f"Ошибка при загрузке {url} (попытка {attempt}/{retries}): {e}")
        except Exception as e:
            last_error = e
            logger.warning(f"Ошибка при обработке изображения {url} (попытка {attempt}/{retries}): {e}")
        
        if attempt < retries:
            time.sleep(backoff_seconds * attempt)
            
    logger.error(f"Не удалось загрузить {url} после {retries} попыток: {last_error}")
    return None

def save_image(image, output_dir="output"):
    """
    Сохраняет изображение с временной меткой в папку с датой.
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Загружаем часовой пояс из конфига
        try:
            SCRIPT_TZ = ZoneInfo(TIMEZONE)
        except Exception:
            logger.warning(f"Не удалось загрузить часовой пояс '{TIMEZONE}'. Используется UTC.")
            SCRIPT_TZ = ZoneInfo("UTC")

        today = datetime.now(SCRIPT_TZ).strftime("%Y%m%d")
        today_folder = os.path.join(output_dir, today)
        os.makedirs(today_folder, exist_ok=True)
        
        timestamp = datetime.now(SCRIPT_TZ).strftime("%Y%m%d_%H%M%S")
        filename = f"merged_tiles_{timestamp}.png"
        filepath = os.path.join(today_folder, filename)
        
        image.save(filepath, "PNG", optimize=True, compress_level=9)
        logger.info(f"Изображение сохранено: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {e}")
        return None

def download_and_crop_area(tl_x, tl_y, tl_px_x, tl_px_y, br_x, br_y, br_px_x, br_px_y):
    """
    Основная функция: скачивает, объединяет, обрезает и масштабирует область.
    
    Args:
        tl_x (int): Координата X верхнего левого тайла.
        tl_y (int): Координата Y верхнего левого тайла.
        tl_px_x (int): Пиксельная координата X внутри верхнего левого тайла.
        tl_px_y (int): Пиксельная координата Y внутри верхнего левого тайла.
        br_x (int): Координата X нижнего правого тайла.
        br_y (int): Координата Y нижнего правого тайла.
        br_px_x (int): Пиксельная координата X внутри нижнего правого тайла.
        br_px_y (int): Пиксельная координата Y внутри нижнего правого тайла.
    """
    logger.info(f"Задана область для скачивания:")
    logger.info(f"  Верхний левый угол: Тайл({tl_x}, {tl_y}), Пиксель({tl_px_x}, {tl_px_y})")
    logger.info(f"  Нижний правый угол: Тайл({br_x}, {br_y}), Пиксель({br_px_x}, {br_px_y})")

    # --- 1. Генерация списка URL-адресов для скачивания ---
    tile_coords_to_download = []
    for y in range(tl_y, br_y + 1):
        row_coords = []
        for x in range(tl_x, br_x + 1):
            row_coords.append({'x': x, 'y': y, 'url': BASE_URL.format(x=x, y=y)})
        tile_coords_to_download.append(row_coords)

    if not tile_coords_to_download:
        logger.error("Не удалось сгенерировать список тайлов. Проверьте координаты.")
        return False

    grid_size_y = len(tile_coords_to_download)
    grid_size_x = len(tile_coords_to_download[0])
    total_tiles = grid_size_x * grid_size_y
    logger.info(f"Требуется скачать {total_tiles} тайлов (сетка {grid_size_x}x{grid_size_y})")

    # --- 2. Параллельная загрузка тайлов ---
    merged_image_size = (grid_size_x * 1000, grid_size_y * 1000)
    merged_image = Image.new('RGBA', merged_image_size, (0, 0, 0, 0))
    
    failed_tiles = []
    successful_tiles = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=total_tiles) as executor:
        future_to_tile = {
            executor.submit(download_image, tile['url']): tile
            for row in tile_coords_to_download for tile in row
        }

        for future in concurrent.futures.as_completed(future_to_tile):
            tile_info = future_to_tile[future]
            try:
                tile_image = future.result()
                if tile_image:
                    # Рассчитываем позицию для вставки
                    col_index = tile_info['x'] - tl_x
                    row_index = tile_info['y'] - tl_y
                    paste_x = col_index * 1000
                    paste_y = row_index * 1000
                    
                    if tile_image.mode != 'RGBA':
                        tile_image = tile_image.convert('RGBA')

                    merged_image.paste(tile_image, (paste_x, paste_y), tile_image)
                    successful_tiles += 1
                    logger.info(f"✅ Тайл ({tile_info['x']},{tile_info['y']}) вставлен. Прогресс: {successful_tiles}/{total_tiles}")
                else:
                    failed_tiles.append(tile_info['url'])
            except Exception as e:
                failed_tiles.append(tile_info['url'])
                logger.error(f"❌ Исключение при обработке тайла {tile_info['url']}: {e}")

    if failed_tiles:
        logger.error(f"❌ ЗАГРУЗКА НЕУДАЧНА: {len(failed_tiles)} из {total_tiles} тайлов не загружены.")
        for url in failed_tiles:
            logger.error(f"  - {url}")
        return False
    
    logger.info("✅ Все тайлы успешно загружены и объединены.")

    # --- 3. Обрезка объединенного изображения ---
    left = tl_px_x
    upper = tl_px_y
    right = (br_x - tl_x) * 1000 + br_px_x
    lower = (br_y - tl_y) * 1000 + br_px_y

    logger.info(f"Вычисляю координаты для обрезки: ({left}, {upper}, {right}, {lower})")
    cropped_image = merged_image.crop((left, upper, right, lower))
    logger.info(f"Изображение успешно обрезано. Новый размер: {cropped_image.size}")

    # --- 4. Масштабирование результата ---
    final_size = (cropped_image.width * SCALE_FACTOR, cropped_image.height * SCALE_FACTOR)
    logger.info(f"Масштабирую изображение до {final_size} (коэффициент {SCALE_FACTOR}x)")
    scaled_image = cropped_image.resize(final_size, Image.Resampling.NEAREST)

    # --- 5. Сохранение итогового изображения ---
    save_image(scaled_image)
    return True

# --- ТОЧКА ВХОДА ---

def main():
    """
    Основная функция для запуска скрипта.
    """
    logger.info("🚀 Запуск скрипта для загрузки области карты")
    
    # Запуск основного процесса
    success = download_and_crop_area(
        tl_x=TOP_LEFT_TILE_X,
        tl_y=TOP_LEFT_TILE_Y,
        tl_px_x=TOP_LEFT_PIXEL_X,
        tl_px_y=TOP_LEFT_PIXEL_Y,
        br_x=BOTTOM_RIGHT_TILE_X,
        br_y=BOTTOM_RIGHT_TILE_Y,
        br_px_x=BOTTOM_RIGHT_PIXEL_X,
        br_px_y=BOTTOM_RIGHT_PIXEL_Y
    )

    if success:
        logger.info("✅ ПРОЦЕСС УСПЕШНО ЗАВЕРШЕН!")
    else:
        logger.error("❌ ПРОЦЕСС ЗАВЕРШИЛСЯ С ОШИБКАМИ.")
        
    return success

if __name__ == "__main__":
    is_successful = main()
    exit(0 if is_successful else 1)