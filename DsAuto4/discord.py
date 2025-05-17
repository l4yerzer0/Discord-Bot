import requests
import time
import random
import concurrent.futures
import json
import os
import logging
from itertools import cycle
from rich.console import Console
from rich.theme import Theme
from rich.logging import RichHandler
from openai import OpenAI
from difflib import SequenceMatcher
import re


# Настройка консоли
console = Console(
    theme=Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
        }
    )
)

# Настройка логирования без дублирования времени
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            markup=False,
            show_path=False,
            show_level=False,
            show_time=False,
        )
    ],
)

# Отключение логгирования запросов HTTP от библиотеки OpenAI
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("discord_bot")

def calculate_nonce() -> str:
        unix_ts = time.time()
        return str((int(unix_ts) * 1000 - 1420070400000) * 4194304)

class CryptoDiscordBot:
    def __init__(self):
        # Загрузка конфигурации
        self.load_gpt_settings()
        self.load_channels()
        self.load_stickers() # Загружаем стикеры
        self.setup_openai()
        self.load_accounts()
        self.load_sentences() # Загружаем предложения

    def load_gpt_settings(self):
        """Загрузка настроек GPT из файла"""
        settings_path = os.path.join(os.getcwd(), "gpt_settings.json")
        try:
            if not os.path.exists(settings_path):
                # файл с настройками по умолчанию
                default_settings = {
                    "api_key": "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",
                    "model": "gpt-4o-mini",
                    "reply_chance": 30,
                    "max_symbols": 500,
                    # bot_personality - определяет личность бота и его стиль общения
                    "bot_personality": "you are a regular crypto user interested in projects respond briefly and informally use simple language 3-7 words without nicknames without emoji without excess punctuation, now in Linera project chat",
                    # message_instructions - определяет, как отвечать на сообщения
                    "message_instructions": "respond naturally as a regular community member and ordinary person without emoji without excess punctuation keep casual style",
                }

                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, ensure_ascii=False, indent=4)

                logger.error(
                    "❌ Файл gpt_settings.json не найден. Создан файл с настройками по умолчанию."
                )
                logger.info(
                    "✅ Настройте файл gpt_settings.json и запустите бота снова."
                )
                exit(0)

            with open(settings_path, "r", encoding="utf-8-sig") as f:
                settings = json.load(f)

            # Загрузка настроек
            self.openai_api_key = settings.get("api_key", "")
            self.gpt_model = settings.get("model", "gpt-4o-mini")
            self.reply_chance = settings.get("reply_chance", 30)
            self.max_symbols = settings.get("max_symbols", 500)
            #self.work_mode = settings.get("work_mode", 1)

            # Загрузка оба промпта
            # bot_personality - основные инструкции по "личности" бота
            self.bot_personality = settings.get("bot_personality", "")
            # message_instructions - инструкции по обработке сообщений
            self.message_instructions = settings.get("message_instructions", "")

            logger.info("✅ Настройки GPT успешно загружены")

        except json.JSONDecodeError:
            logger.error("❌ Ошибка в формате JSON файла gpt_settings.json")
            exit(1)
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке настроек GPT: {e}")
            exit(1)

    def load_channels(self):
        """Загрузка каналов из файла"""
        channels_path = os.path.join(os.getcwd(), "channels.json")
        try:
            if not os.path.exists(channels_path):
                # файл с каналами по умолчанию
                default_channels = [{"id": "ID_КАНАЛА", "interval": [60, 120]}]

                with open(channels_path, "w", encoding="utf-8") as f:
                    json.dump(default_channels, f, ensure_ascii=False, indent=4)

                logger.error(
                    "❌ Файл channels.json не найден. Создан файл с настройками по умолчанию."
                )
                logger.info("✅ Настройте файл channels.json и запустите бота снова.")
                exit(0)

            with open(channels_path, "r", encoding="utf-8-sig") as f:
                self.all_channels = json.load(f)

            logger.info(f"✅ Загружено {len(self.all_channels)} каналов")

        except json.JSONDecodeError:
            logger.error("❌ Ошибка в формате JSON файла channels.json")
            exit(1)
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке каналов: {e}")
            exit(1)

    def load_stickers(self):
        """Загрузка стикеров из файла stickers.json"""
        stickers_path = os.path.join(os.getcwd(), "stickers.json")
        try:
            if not os.path.exists(stickers_path):
                # файл с стикерами по умолчанию
                default_stickers = {"default": ["STICKER_ID"]}

                with open(stickers_path, "w", encoding="utf-8") as f:
                    json.dump(default_stickers, f, ensure_ascii=False, indent=4)

                logger.error(
                    "❌ Файл stickers.json не найден. Создан файл с настройками по умолчанию."
                )
                logger.info("✅ Настройте файл stickers.json и запустите бота снова.")
                exit(0)

            with open(stickers_path, "r", encoding="utf-8-sig") as f:
                self.stickers = json.load(f)

            logger.info(f"✅ Загружены настройки стикеров")

        except json.JSONDecodeError:
            logger.error("❌ Ошибка в формате JSON файла stickers.json")
            exit(1)
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке стикеров: {e}")
            exit(1)

    def setup_openai(self):
        """Настройка клиента OpenAI"""
        try:
            if (
                not self.openai_api_key
                or self.openai_api_key == "ВВЕДИ_API_КЛЮЧ"
            ):
                logger.error("❌ Отсутствует API ключ")
                exit(1)

            self.client = OpenAI(api_key=self.openai_api_key)
            logger.info("✅ OpenAI клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации OpenAI: {e}")
            exit(1)

    
    def load_accounts(self):
        """Загрузка токенов и прокси"""
        try:
            # Проверка наличия файлов
            if not os.path.exists("discord_tokens.txt"):
                logger.error("❌ Файл discord_tokens.txt не найден")
                with open("discord_tokens.txt", "w") as f:
                    f.write("# Вставьте токены Discord, по одному на строку\n")
                logger.info("✅ Создан пустой файл discord_tokens.txt")
                exit(0)

                # проверка прокси(пока не надо)
            # if not os.path.exists("proxies.txt"):
            #   logger.error("❌ Файл прокси не найден")
            #  with open("proxies.txt", "w") as f:
            #     f.write(
            #        "# прокси, по одному на строку\n# Формат: ip:port или ip:port:username:password\n"
            #    )
            # logger.info("✅ Создан пустой файл прокси")
            # exit(0)
            self.accounts = []
            #self.tokens = []
            self.account_usernames = []
            self.accounts_info =[]
            # Загрузка токенов
            with open("discord_tokens.txt", "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(":")
                        token = parts[0].strip()
                        account_username = parts[1].strip() if len(parts) > 1 else None
                        self.accounts.append(token)
                        self.account_usernames.append(account_username)
                        self.accounts_info.append(
                                {
                                    "token": token,
                                    "name": account_username,
                                }
                            )

            # Загрузка прокси
            # with open("proxies.txt", "r") as f:
            #   self.proxies = [
            #      line.strip()
            #     for line in f.readlines()
            #    if line.strip() and not line.strip().startswith("#")
            # ]

            if not self.accounts:
                logger.error("❌ Нет токенов Дискорд")
                exit(1)

            # проверка наличия прокси
            # if not self.proxies:
            #   logger.error("❌ Нет прокси")
            #  exit(1)

            # Проверка соотношения токенов и прокси
            # if len(self.tokens) > len(self.proxies):
            #   logger.error("❌ Токенов больше чем прокси; !1 аккаунт = 1 прокси!")
            #  exit(1)

            # Создание аккаунтов (пары токен-прокси)
            #self.accounts = self.tokens  # list(zip(self.tokens, cycle(self.proxies)))

            logger.info(
                f"✅ Загружено {len(self.accounts)} аккаунтов"  # и {len(self.proxies)} прокси"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке аккаунтов: {e}")
            exit(1)

    def load_sentences(self):
        """Загрузка предложений из файла sentences.json"""
        sentences_path = os.path.join(os.getcwd(), "sentences.json")
        try:
            if not os.path.exists(sentences_path):
                # файл с предложениями по умолчанию
                default_sentences = ["Hello", "How are you?", "What's up?"]

                with open(sentences_path, "w", encoding="utf-8") as f:
                    json.dump(default_sentences, f, ensure_ascii=False, indent=4)

                logger.error(
                    "❌ Файл sentences.json не найден. Создан файл с настройками по умолчанию."
                )
                logger.info("✅ Настройте файл sentences.json и запустите бота снова.")
                exit(0)

            with open(sentences_path, "r", encoding="utf-8-sig") as f:
                self.sentences = json.load(f)

            logger.info(f"✅ Загружено {len(self.sentences)} предложений")

        except json.JSONDecodeError:
            logger.error("❌ Ошибка в формате JSON файла sentences.json")
            exit(1)
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке предложений: {e}")
            exit(1)

    def prepare_proxy_config(self, proxy):
        """Преобразует строку прокси в словарь для requests"""
        parts = proxy.split(":")
        if len(parts) == 2:  # ip:port
            ip, port = parts
            return {"http": f"http://{ip}:{port}", "https": f"http://{ip}:{port}"}
        elif len(parts) == 4:  # ip:port:username:password
            ip, port, user, password = parts
            return {
                "http": f"http://{user}:{password}@{ip}:{port}",
                "https": f"http://{user}:{password}@{ip}:{port}",
            }
        return None

    def fetch_channel_history(
        self, token, channel_id, token_suffix, limit=5
    ):  # proxy,
        """Получение истории сообщений из канала Discord"""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"
        headers = {"Authorization": token, "Content-Type": "application/json"}
        # proxy_dict = self.prepare_proxy_config(proxy)

        try:
            response = requests.get(
                url, headers=headers, timeout=10  # proxies=proxy_dict,
            )
            if response.status_code == 200:
                messages = response.json()

                # Отфильтрует  сообщения от ботов
                filtered_messages = [
                    msg
                    for msg in messages
                    if not msg.get("author", {}).get("bot", False)
                    and msg.get("author", {}).get("username") not in self.account_usernames
                ]
                filtered_messages.reverse()  # От старых к новым
                # for msg in filtered_messages:
                # author =
                # console.print(msg.get("author", {}).get("username"))
                # time.sleep(1000)

                return filtered_messages

            else:
                logger.error(
                    f"❌ {token_suffix}: Ошибка получения сообщений: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"❌ {token_suffix}: Ошибка запроса: {e}")
        return []

    previous_responses = []  # история ответов

    def create_ai_reply(self, chat_history, target_message):
        """Генерация ответа"""
        try:
            # Формирование контекста из истории чата
            conversation_context = "\n".join(
                [
                    f"{msg.get('author', {}).get('username', 'User')}: {msg.get('content', '')}"
                    for msg in chat_history
                ]
            )

            # Получаем информацию о сообщении, на которое отвечаем
            target_username = target_message.get("author", {}).get("username", "User")
            target_content = target_message.get("content", "")

            # Создание запроса с контекстом сообщений
            prompt_with_context = (
                f"Here are messages from a Discord crypto community chat:\n{conversation_context}\n\n"
                f'Reply specifically to {target_username}\'s message: "{target_content}". '
                f"Your reply should be relevant to this specific message while considering the overall chat context. {self.message_instructions}"
            )

            # Запрос с явным указанием кодировки UTF-8
            ai_response = self.client.chat.completions.create(
                model=self.gpt_model,
                messages=[
                    # bot_personality
                    {"role": "system", "content": self.bot_personality},
                    # Сообщение с контекстом и инструкциями
                    {"role": "user", "content": prompt_with_context},
                ],
                max_tokens=150,
                temperature=0.7,  # Вариативность ответа, больше значение = больше вариативность
            )

            # Получение и возврат ответа
            ai_reply = ai_response.choices[0].message.content
            return ai_reply

        except UnicodeEncodeError as e:
            logger.error(f"❌ Ошибка кодировки при обработке сообщения: {e}")

            # запрос без контекста чата
            try:
                simple_response = self.client.chat.completions.create(
                    model=self.gpt_model,
                    messages=[
                        {"role": "system", "content": self.bot_personality},
                        {
                            "role": "user",
                            "content": f"Generate a short crypto message responding to '{target_content}' according to your personality",
                        },
                    ],
                    max_tokens=150,
                    temperature=0.7,
                )
                return simple_response.choices[0].message.content
            except Exception as simple_error:
                logger.error(
                    f"❌ Не удалось получить ответ без контекста: {simple_error}"
                )
                return ""

        except Exception as e:
            logger.error(f"❌ Ошибка при создании ответа: {e}")
            return ""

    def create_general_reply(self, chat_history):
        """Создание общего ответа в тему разговора"""
        try:
            # Формируем контекст из истории чата
            conversation_context = "\n".join(
                [
                    f"{msg.get('author', {}).get('username', 'User')}: {msg.get('content', '')}"
                    for msg in chat_history
                ]
            )

            # Сначала извлекаем основную тему обсуждения
            topic_prompt = (
                f"Here are the last messages from a Discord crypto conversation:\n{conversation_context}\n\n"
                f"In 2-3 words, what specific topic are they discussing right now? Just name the topic, no explanation."
            )

            # Запрос к AI для определения темы
            topic_response = self.client.chat.completions.create(
                model=self.gpt_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract the main topic from conversations.",
                    },
                    {"role": "user", "content": topic_prompt},
                ],
                max_tokens=10,
                temperature=0.3,
            )

            # Получаем тему разговора
            current_topic = topic_response.choices[0].message.content.strip()

            # Создаем запрос для ответа в тему разговора с учетом выявленной темы
            prompt_with_context = (
                f"Here are messages from a Discord crypto chat:\n{conversation_context}\n\n"
                f"The current topic is: {current_topic}\n"
                f"Write ONE natural short message (3-7 words) that continues this specific discussion. "
                f"Don't repeat others but add something relevant to THIS EXACT topic. "
                f"No usernames, no summaries, just one authentic short contribution. {self.message_instructions}"
            )

            # Запрос к AI
            ai_response = self.client.chat.completions.create(
                model=self.gpt_model,
                messages=[
                    {"role": "system", "content": self.bot_personality},
                    {"role": "user", "content": prompt_with_context},
                ],
                max_tokens=150,
                temperature=0.7,
            )

            # Получаем и возвращаем ответ
            ai_reply = ai_response.choices[0].message.content

            # Логируем определенную тему для отладки
            logger.info(f"📌 Определена тема: {current_topic}, генерация сообщения")

            return ai_reply

        except UnicodeEncodeError as e:
            logger.error(f"❌ Ошибка кодировки при обработке сообщения: {e}")

            # Пробуем запрос без контекста чата
            try:
                simple_response = self.client.chat.completions.create(
                    model=self.gpt_model,
                    messages=[
                        {"role": "system", "content": self.bot_personality},
                        {
                            "role": "user",
                            "content": "Generate a short crypto message about a random topic according to your personality",
                        },
                    ],
                    max_tokens=150,
                    temperature=0.7,
                )
                return simple_response.choices[0].message.content
            except Exception as simple_error:
                logger.error(
                    f"❌ Не удалось получить общий ответ без контекста: {simple_error}"
                )
                return ""

        except Exception as e:
            logger.error(f"❌ Ошибка при создании общего ответа AI: {e}")
            return ""

    def filter_ai_response(self, response_text):
        """
        Фильтрует ответ AI, оставляя только текст самого ответа (без цитат).
        
        Правила фильтрации:
        1. Если в строке содержатся форматы типа "username: text", она считается цитатой
        2. Удаляет строки с метками ответа "(ответ):"
        3. Берется только последний блок содержательного текста (после всех цитат)
        
        Args:
            response_text (str): Полный текст ответа от AI
            
        Returns:
            str: Отфильтрованный текст ответа
        """
        
        # Если текст пустой, возвращаем его как есть
        if not response_text or not response_text.strip():
            return response_text
            
        # Разделяем текст на строки
        lines = response_text.split('\n')
        
        # Очищаем пустые строки и применяем strip()
        lines = [line.strip() for line in lines if line.strip()]
        
        # Если текст пустой после очистки, возвращаем исходный
        if not lines:
            return response_text
        
        # Шаблоны для поиска цитат и меток ответов
        username_pattern = re.compile(r'^[a-zA-Z0-9_-]+\s*:')
        reply_label_pattern = re.compile(r'^\(ответ\):', re.IGNORECASE)
        
        # Находим индекс последней строки, которая похожа на цитату
        last_citation_index = -1
        for i, line in enumerate(lines):
            # Проверяем, является ли строка цитатой или меткой ответа
            if username_pattern.match(line) or reply_label_pattern.match(line):
                last_citation_index = i
        
        # Берем все строки после последней цитаты
        result_lines = lines[last_citation_index + 1:] if last_citation_index < len(lines) - 1 else []
        
        # Если после фильтрации ничего не осталось, возвращаем исходный текст
        if not result_lines:
            return response_text
        
        # Соединяем оставшиеся строки
        result = '\n'.join(result_lines)
        
        return result.strip()

    def add_reaction(self, token, channel_id, message_id, emoji):
        """Добавляет реакцию на сообщение"""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        headers = {"Authorization": token}

        try:
            response = requests.put(url, headers=headers)
            if response.status_code == 204:
                logger.info(f"✅ Реакция {emoji} добавлена к сообщению {message_id}")
                return True
            else:
                logger.error(
                    f"❌ Ошибка добавления реакции {emoji} к сообщению {message_id}: {response.status_code}"
                )
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении реакции: {e}")
            return False

    def post_discord_message(self, token, channel_id, content, reply_to=None):  # proxy,
        """Отправка сообщения в канал Discord"""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {"Authorization": token, "Content-Type": "application/json"}
        # использование прокси
        # proxy_dict = self.prepare_proxy_config(proxy)
        data = {"content": content}
        if reply_to:
            data["message_reference"] = {"message_id": reply_to}

        try:
            response = requests.post(
                url, json=data, headers=headers, timeout=10  # proxies=proxy_dict
            )
            if response.status_code == 200:
                message_id = response.json().get("id")  # Получаем ID отправленного сообщения
                return True, response, message_id  # Возвращаем ID сообщения
            else:
                logger.error(
                    f"❌ Ошибка отправки сообщения в канал #{channel_id}: {response.status_code} - {response.text}"
                )
                return False, response, None
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return False, None, None
        
    def delete_discord_message(self, token, channel_id, message_id):
        """Удаляет сообщение в канале Discord"""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
        headers = {"Authorization": token}

        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                logger.info(f"✅ Сообщение {message_id} удалено из канала #{channel_id}")
                return True
            else:
                logger.error(
                    f"❌ Ошибка при удалении сообщения {message_id} из канала #{channel_id}: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении сообщения: {e}")
            return False
    
    
    def post_discord_sticker(self, token, channel_id, sticker_id, reply_to=None):
        """Отправка стикера в канал Discord"""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {"Authorization": token, "Content-Type": "application/json"}
        sticker_id = str(sticker_id).strip()
        data = {"sticker_ids": [sticker_id]}
        if reply_to:
            data["message_reference"] = {"message_id": reply_to}

        try:
            response = requests.post(
                url, json=data, headers=headers, timeout=10  # proxies=proxy_dict
            )
            logging.info(f"Ответ: Status Code={response.status_code}, Text={response.text}") # Логирование ответа
            if response.status_code == 200:
                #logger.info(f"✅ Стикер {sticker_id} отправлен в канал #{channel_id}")
                return True, response
            else:
                logger.error(
                    f"❌ Ошибка отправки стикера {sticker_id} в канал #{channel_id}: {response.status_code} - {response.text}"
                )
                return False, response
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return False, None

    def handle_channel(
        self, token, channel_config, token_suffix, message_limit, messages_sent
    ):  # proxy,
        """Обработка одного канала"""
        channel_id = channel_config.get("id")
        interval = channel_config.get("interval", [60, 120])

        # шанс реакции и список емоджи
        reaction_chance = 30
        sticker_chance = 7  # шанс отправки стикера вместо сообщения
        server_name = channel_config.get("server")  # Получаем название сервера
        emojis = ["👍", "🔥", "💯", "😂", "🤔"]
        
        # Отслеживаем последние сообщения, на которые мы ответили
        # для предотвращения бесконечных циклов ответов
        last_replied_messages = set()  # Множество ID сообщений, на которые недавно отвечали
        max_tracked_messages = 10  # Максимальное количество отслеживаемых сообщений
        
        # Словарь для отслеживания наших собственных сообщений
        own_messages = {}  # формат: {message_id: timestamp}
        max_own_messages = 20  # Максимальное количество отслеживаемых собственных сообщений

        while True:  # бесконечный цикл для работы с каналом
            try:
                # Получение истории чата из канала
                channel_history = self.fetch_channel_history(
                    token, channel_id, token_suffix  # proxy,
                )
                if not channel_history:
                    logger.warning(
                        f"⚠️ {token_suffix}: Нет сообщений в канале {channel_id}"
                    )
                    time.sleep(10)  # Короткая задержка при пустой истории
                    continue  # Переход к следующей итерации

                # Проверяем, есть ли ответы на наши сообщения
                reply_needed = False
                target_message = None
                
                for msg in channel_history:
                    # Проверка, является ли сообщение ответом на наше
                    msg_id = msg.get("id")
                    referenced_message_id = msg.get("referenced_message", {}).get("id")
                    
                    if referenced_message_id in own_messages:
                        # Кто-то ответил на наше сообщение
                        msg_author = msg.get("author", {})
                        
                        # Проверяем, не бот ли это автор и не мы ли сами
                        if not msg_author.get("bot", False) and (
                            self.account_usernames is None or msg_author.get("username") != self.account_usernames
                        ):
                            # Проверяем, не отвечали ли мы уже на это сообщение (предотвращение циклов)
                            if msg_id not in last_replied_messages:
                                reply_needed = True
                                target_message = msg
                                # Добавляем ID в список сообщений, на которые уже ответили
                                last_replied_messages.add(msg_id)
                                # Если список слишком большой, удаляем старые элементы
                                if len(last_replied_messages) > max_tracked_messages:
                                    last_replied_messages.pop()  # Удаляем случайный элемент
                                break  # Нашли сообщение для ответа, выходим из цикла
                
                # Если нет срочных ответов, работаем в обычном режиме по интервалу
                if not reply_needed:
                    if isinstance(interval, (list, tuple)):
                        wait_time = random.uniform(interval[0], interval[1])
                    else:
                        wait_time = interval
                    
                    # Обычный режим  
                    if self.work_mode == 1:
                        #  Фильтрация сообщений от ботов и от себя
                        filtered_history = [
                            msg
                            for msg in channel_history
                            if not msg.get("author", {}).get("bot", False)
                            and (
                                self.account_usernames is None
                                or msg.get("author", {}).get("username") != self.account_usernames
                            )
                        ]

                        if not filtered_history:
                            logger.warning(
                                f"⚠️ {token_suffix}: Нет сообщений для ответа после фильтрации в канале {channel_id}"
                            )
                            time.sleep(wait_time)
                            continue  # Переход к следующей итерации

                        # Выбор случайного сообщения для ответа (теперь из отфильтрованной истории)
                        target_message = random.choice(filtered_history)
                    
                    # Проверка лимита сообщений в любом случае
                    if message_limit > 0 and messages_sent[0] >= message_limit:
                        logger.info(
                            f"✅ {token_suffix}: Все сообщения отправлены ({message_limit}). Завершение работы в канале #{channel_id}."
                        )
                        break  # Завершаем работу в канале
                    
                # Создаем ответ для целевого сообщения
                # Определяет, будет ли отвечать на сообщение с указанием на него
                reply_id = None
                # Если это ответ на чей-то ответ на наше сообщение, всегда используем reply
                if reply_needed:
                    reply_id = target_message.get("id")
                # Иначе используем обычную логику с reply_chance
                elif random.randint(1, 100) <= self.reply_chance:
                    reply_id = target_message.get("id")
                
                # ЗДЕСЬ ОПРЕДЕЛЯЕМ, БУДЕТ СТИКЕР ИЛИ СООБЩЕНИЕ
                # Получаем список стикеров для текущего сервера
                available_stickers = self.stickers.get(server_name, self.stickers.get("default", []))
                
                # Определяем, будет отправлен стикер или обычное сообщение
                send_sticker = random.randint(1, 100) <= sticker_chance and available_stickers
                
                if send_sticker:
                    # Отправляем стикер вместо сообщения
                    sticker_id = random.choice(available_stickers)
                    success, response = self.post_discord_sticker(
                        token, channel_id, sticker_id, reply_id
                    )
                    if success:
                        logger.info(f"✅ {token_suffix}: Стикер {sticker_id} отправлен в канал #{channel_id} (вместо сообщения)")
                        messages_sent[0] += 1  # Увеличиваем счетчик
                    else:
                        if response:
                            logger.error(
                                f"❌ {token_suffix}: Ошибка отправки стикера {sticker_id}: {response.status_code} - {response.text}"
                            )
                else:
                    # Отправляем обычное сообщение
                    raw_response = self.create_ai_reply(filtered_history if not reply_needed else [target_message], target_message)
                    
                    # Фильтруем ответ, чтобы убрать цитаты и оставить только текст от бота
                    reply_content = self.filter_ai_response(raw_response)
                    
                    if not reply_content or len(reply_content) > self.max_symbols:
                        logger.warning(
                            f"⚠️ {token_suffix}: Сообщение превышает лимит или пустое"
                        )
                        if not reply_needed:
                            time.sleep(wait_time)
                        else:
                            time.sleep(10)  # Короткая задержка при ошибке в срочном ответе
                        continue  # Переход к следующей итерации
                    
                    success, response, message_id = self.post_discord_message(
                        token, channel_id, reply_content, reply_id  # proxy,
                    )
                    if success:
                        reply_info = " (срочный ответ)" if reply_needed else " (ответ)" if reply_id else ""
                        next_msg_time = time.strftime(
                            "%H:%M:%S", time.localtime(time.time() + (wait_time if not reply_needed else 60))
                        )
                        logger.info(
                            f"✅ {token_suffix} -> #{channel_id}{reply_info}: {reply_content} | Следующее сообщение в {next_msg_time}"
                        )
                        messages_sent[0] += 1  # Увеличиваем счетчик
                        
                        # Сохраняем информацию о нашем сообщении для отслеживания ответов на него
                        current_time = time.time()
                        own_messages[message_id] = current_time
                        
                        # Удаляем старые сообщения из отслеживания
                        if len(own_messages) > max_own_messages:
                            # Находим и удаляем самое старое сообщение
                            oldest_msg_id = min(own_messages.items(), key=lambda x: x[1])[0]
                            own_messages.pop(oldest_msg_id)
                        
                        #self.delete_discord_message(token, channel_id, message_id) # <-- Раскомментируйте, если нужно удалять сообщение
                    else:
                        if response:
                            logger.error(
                                f"❌ {token_suffix}: Ошибка {response.status_code}: {response.text}"
                            )
                
                # Добавляем реакцию с определенным шансом (независимо от того, отправили мы стикер или сообщение)
                if random.randint(1, 100) <= reaction_chance:
                    emoji = random.choice(emojis)
                    self.add_reaction(token, channel_id, target_message.get("id"), emoji)

                # ожидание перед следующей отправкой
                # Если это был срочный ответ, делаем меньшую задержку
                if reply_needed:
                    time.sleep(20)  # Ждем немного после срочного ответа
                else:
                    time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"❌ {token_suffix}: Ошибка в канале #{channel_id}: {e}")
                time.sleep(60)  # Ждем минуту при ошибке

    def choose_accounts(self):
        """Выводит список аккаунтов и позволяет пользователю выбрать нужные."""
        console.print("[bold]Доступные аккаунты:[/]")
        for i, account_info in enumerate(self.accounts_info):
            console.print(f"{i+1}. {account_info['name']} (Токен: {account_info['token'][:8]}...)") # Показываем только первые 8 символов токена

        while True:
            choice = console.input(
                "[prompt]Введите номера аккаунтов через запятую (или нажмите Enter для выбора всех): [/]"
            )
            if not choice:
                return self.accounts_info  # Выбраны все аккаунты
            try:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(",")]
                selected_accounts = [self.accounts_info[i] for i in selected_indices]
                return selected_accounts
            except (ValueError, IndexError):
                console.print("[bold red]Неверный ввод. Пожалуйста, повторите.[/]")

    def account_worker(self, token, idx):  # proxy,
        """Рабочий процесс для одного аккаунта"""
        token_suffix = f"Account #{idx+1}"  # Только номер аккаунта, без токена

        # Запрашиваем количество сообщений для отправки
        while True:
            try:
                message_limit = int(
                    console.input(
                        f"[prompt]Введите количество сообщений для аккаунта {token_suffix} (или 0 для бесконечной работы): [/]"
                    )
                )
                if message_limit >= 0:
                    break
                else:
                    console.print("[bold red]Пожалуйста, введите неотрицательное число.[/]")
            except ValueError:
                console.print("[bold red]Неверный ввод. Пожалуйста, введите число.[/]")

        # Выбор каналов для аккаунта
        selected_channels = self.choose_channels(self.all_channels)
        #счетчик
        messages_sent = [0]

        # Многопоточность рабочих потоков для каналов
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []

            # Запуск обработка каждого канала в отдельном потоке
            for channel_config in selected_channels:
                future = executor.submit(
                    self.handle_channel, token, channel_config, token_suffix, message_limit,  # Передаем лимит в handle_channel
                    messages_sent,  # proxy,
                )
                futures.append(future)
                time.sleep(15)  # Пауза между запуском каналов

            # Ждем завершения всех потоков (они не должны завершаться, т.к. содержат бесконечный цикл)
            for future in concurrent.futures.as_completed(futures):
                try:
                    messages_sent += future.result()
                    future.result()
                    logger.error(
                        f"❌ {token_suffix}: Канальный поток завершился (не должен)"
                    )
                except Exception as e:
                    logger.error(f"❌ {token_suffix}: Ошибка в канальном потоке: {e}")

                if message_limit > 0 and messages_sent >= message_limit:
                    logger.info(
                        f"✅ {token_suffix}: Достигнут лимит сообщений ({message_limit}). Завершение работы аккаунта."
                    )
                    return #Завершаем работу аккаунта

        logger.error(f"❌ {token_suffix}: Аккаунт завершил работу (не должен)")

    def run(self):

        self.work_mode = self.choose_work_mode()
        # Выбор аккаунтов для запуска
        selected_accounts = self.choose_accounts()

        """Запуск аккаунтов"""
        # Вывод информации о старте
        self.print_welcome()
        

        # Запуск каждого аккаунта в отдельном потоке
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(selected_accounts)
        ) as executor:
            futures = []

            for idx, (account_info) in enumerate(
                selected_accounts
            ):  # , proxy
                token = account_info["token"]
                logger.info(f"🚀 Запуск аккаунта #{idx+1}/{len(selected_accounts)}: {account_info['name']}...")
                futures.append(
                    executor.submit(self.account_worker, token, idx)
                )  # proxy,

                # Небольшая задержка между запуском аккаунтов
                if idx < len(selected_accounts) - 1:
                    delay = random.uniform(15, 20)
                    logger.info(
                        f"⏱️ Ожидание {delay:.2f} секунд перед запуском следующего..."
                    )
                    time.sleep(delay)

            # выход будет обработан на уровне основного скрипта
            concurrent.futures.wait(futures)

    def print_welcome(self):
        """Вывод приветственного сообщения"""
        console.print("\n[bold cyan]╔═══════════════════════════════════════╗[/]")
        console.print("[bold cyan]║    DISCORD AUTO BOT v0.4     ║[/]")
        console.print("[bold cyan]╚═══════════════════════════════════════╝[/]")
        #console.print(
        #    "\n[bold green]• Аккаунтов загружено:[/] " + str(len(self.accounts))
        #)
        # console.print("[bold green]• Прокси загружено:[/] " + str(len(self.proxies)))
        console.print(
            "[bold green]• Каналов для мониторинга:[/] " + str(len(self.all_channels))
        )
        console.print("[bold green]• Модель GPT:[/] " + self.gpt_model)
        console.print(
            "[bold green]• Шанс ответа на сообщение:[/] " + str(self.reply_chance) + "%"
        )
        console.print("\n[bold yellow]Запуск...[/]\n")

    def choose_work_mode(self):
        console.print("[bold green]Выберите режим:[/]")

        while True:
            choice = int(console.input("[prompt]1 - GPT режим; 2 - спам режим : [/]"))
            if not choice:
                selected_mode = 1
                return selected_mode
            try:
                if choice == 1 or choice == 2:
                    selected_mode = choice
                else:
                    selected_mode = None
                if selected_mode is None:
                    console.print("[bold red]Неверный ввод")
                else:
                    return selected_mode
            except (ValueError, IndexError):
                console.print("[bold red]Неверный ввод. Пожалуйста, повторите.[/]")

    def choose_channels(self, channels):
        """Выводит список каналов и позволяет пользователю выбрать нужные."""
        console.print("[bold green]Доступные каналы:[/]")
        for i, channel in enumerate(channels):
            console.print(f"{i+1}. {channel['name']} (ID: {channel['id']})")

        while True:
            choice = console.input(
                "[prompt]Введите номера каналов через запятую (или нажмите Enter для выбора всех): [/]"
            )
            if not choice:
                return channels  # Выбраны все каналы
            try:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(",")]
                selected_channels = [channels[i] for i in selected_indices]
                return selected_channels
            except (ValueError, IndexError):
                console.print("[bold red]Неверный ввод. Пожалуйста, повторите.[/]")

if __name__ == "__main__":
    import sys

    # Перехват Ctrl+C
    def ctrl_c_handler():
        def handler(signum, frame):
            sys.exit(0)  # завершение
            print("[bold red]Остановлено вручную.[/]")

        return handler

    # Регистрация обработчика
    import signal

    signal.signal(signal.SIGINT, ctrl_c_handler())

    try:
        bot = CryptoDiscordBot()
        bot.run()
    except Exception as e:
        console.print(f"\n[bold red]Критическая ошибка: {e}[/]")