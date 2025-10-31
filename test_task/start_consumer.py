import os
import django
import asyncio
import logging
import time
from kafka.errors import NoBrokersAvailable

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_task.settings')
django.setup()

from notification_service.consumers import NotificationConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска consumer"""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Попытка запуска consumer ({attempt + 1}/{max_retries})...")
            
            consumer = NotificationConsumer()
            logger.info("Consumer успешно создан, начинаем обработку сообщений...")
            
            await consumer.start_consuming()
            
        except NoBrokersAvailable as e:
            logger.warning(f"Kafka недоступна ({attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Повторная попытка через {retry_delay} секунд...")
                time.sleep(retry_delay)
            else:
                logger.error("Не удалось подключиться к Kafka после всех попыток")
                raise
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки...")
            break
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка в consumer: {e}")
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == '__main__':
    logger.info("Запуск Kafka Consumer...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        logger.info("Consumer завершил работу")