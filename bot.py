# Библиотеки
import socket
import asyncio
import aiomysql
import aiohttp
import aiocron
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, Defaults
from telegram.error import TelegramError
import os
import sys

# Константы, в докере скорее всего они в другом файле лежать будут
TELEGRAM_TOKEN = "8139176908:AAG--Al0otnn8v9pMzbuC2ei4Y_sQGGp8SY"
MYSQL_HOST = "localhost"
MYSQL_USER = "site"
MYSQL_PASSWORD = "E3KrVXH8cgGY2DMk9njuxz"
MYSQL_DB = "media_1511"
UPDATE_URL = ""

if os.path.exists("/opt/app/sockets/sock1.s"):
    os.remove("/opt/app/sockets/sock1.s")

async def send_telegram_message(bot: Bot, chatid: str, message: str): # Функция отправки сообщения
    try:
        await bot.send_message(chat_id=chatid, text=message)
    except TelegramError as e:
        print(f"Ошибка Telegram: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

# Две функции ниже отвечают за прием сообщения от сайта и отправки его пользователям
async def _handle_client(reader, writer, bot: Bot):
    try:
        data = await reader.read(1024)
        message = data.decode('utf-8').strip().split("separator")
        if message[0]:
            await send_telegram_message(bot, message[0], message[1])
    except Exception as e:
        print(f"Ошибка клиента: {e}")
    finally:
        writer.close()

async def handle_socket_connection(bot: Bot):
    while True:
        try:
            # Создаем Unix сокет вручную
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind("/opt/app/sockets/sock1.s")
            os.chmod("/opt/app/sockets/sock1.s", 0o666)
            
            # Передаем сокет через параметр `sock`
            server = await asyncio.start_server(
                lambda r, w: _handle_client(r, w, bot),
                sock=sock  # Используем созданный сокет
            )
            
            async with server:
                await server.serve_forever()
        except Exception as e:
            print(f"Ошибка сокета: {e}. Перезапуск через 10 сек...")
            await asyncio.sleep(10)
        finally:
            sock.close()

# Функция команды /link login
async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id # id пользователя ( в тг )
        args = context.args
        
        if not args:
            await update.message.reply_text("Введите ваш логин")
            return

        login_email = args[0]
        connection = None
        
        try:
            connection = await aiomysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                loop=asyncio.get_event_loop()
            )
            
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT teleg_change FROM peoples WHERE login_email = %s", (login_email,)) # Проверка на существование
                result = await cursor.fetchone()

                if not result:
                    await update.message.reply_text("Пользователь с таким логином не найден")
                    return

                await cursor.execute("UPDATE peoples SET teleg_change = %s WHERE login_email = %s", (user_id, login_email)) # Отправка уведомления на сайт
                await connection.commit()

            await update.message.reply_text("Подтвердите привязку в личном кабинете, в разделе \"Настройки\"")

        except Exception as e:
            print(f"Ошибка MySQL: {e}")
            await update.message.reply_text("Ошибка при обновлении данных")
        finally:
            if connection:
                connection.close()
                
    except Exception as e:
        print(f"Ошибка команды /link: {e}")
        await update.message.reply_text("Произошла ошибка")

async def changepass_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id # id пользователя ( в тг )
        connection = None
        
        try:
            connection = await aiomysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                loop=asyncio.get_event_loop()
            )
            
            async with connection.cursor() as cursor:
                await cursor.execute("UPDATE `peoples` SET `pass` = `newpass`, `newpass` = NULL WHERE (`newpass` IS NOT NULL) and (`telegram` = %s)", (user_id,)) # смена
                affected_rows = cursor.rowcount
                await connection.commit()

            if affected_rows > 0:
                await update.message.reply_text("Пароль изменен")
            else:
                await update.message.reply_text("Нет активных запросов")

        except Exception as e:
            print(f"Ошибка MySQL: {e}")
            await update.message.reply_text("Ошибка при обновлении данных")
        finally:
            if connection:
                connection.close()
                
    except Exception as e:
        print(f"Ошибка команды /link: {e}")
        await update.message.reply_text("Произошла ошибка")
        
async def notchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id # id пользователя ( в тг )
        connection = None
        
        try:
            connection = await aiomysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                loop=asyncio.get_event_loop()
            )
            
            async with connection.cursor() as cursor:
                await cursor.execute("UPDATE `peoples` SET `newpass` = NULL WHERE (`newpass` IS NOT NULL) and (`telegram` = %s)", (user_id,)) # смена
                affected_rows = cursor.rowcount
                await connection.commit()

            if affected_rows > 0:
                await update.message.reply_text("Смена пароля отклонена")
            else:
                await update.message.reply_text("Нет активных запросов")

        except Exception as e:
            print(f"Ошибка MySQL: {e}")
            await update.message.reply_text("Ошибка при обновлении данных")
        finally:
            if connection:
                connection.close()
                
    except Exception as e:
        print(f"Ошибка команды /link: {e}")
        await update.message.reply_text("Произошла ошибка")

async def update_code():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(UPDATE_URL) as response:
                if response.status == 200:
                    new_code = await response.text()
                    with open(__file__, 'w') as f:
                        f.write(new_code)
                    print("Код обновлен. Перезапуск...")
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    print(f"Ошибка загрузки: {response.status}")
    except Exception as e:
        print(f"Ошибка обновления: {e}")

@aiocron.crontab('20 9 * * *')  # Каждый день в 21:00
async def scheduled_update():
    await update_code()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE): # Сюда скидываются все ошибки которые невозможно обработать
    print(f"Глобальная ошибка: {context.error}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build() # билд бота
    
    application.add_handler(CommandHandler("link", link_command)) # линк функции и команды в боте
    application.add_handler(CommandHandler("changepass", changepass_command))
    application.add_handler(CommandHandler("notchange", notchange_command))
    
    scheduled_update.start()

    application.add_error_handler(error_handler) # обработчик ошибок
    
    # Ниже строки для функционирования бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.create_task(handle_socket_connection(application.bot))
    loop.run_until_complete(application.run_polling())

if __name__ == "__main__":
    main()
