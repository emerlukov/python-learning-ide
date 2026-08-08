"""
AI Agent для Python Learning IDE
Поддержка: Groq (основной) + Google Gemini (fallback)
"""

import threading
import json
import os
from typing import Optional, Callable, List, Dict
from kivy.clock import Clock

try:
    import requests
except ImportError:
    requests = None


class AIAgent:
    """Умный тьютор Python с поддержкой нескольких провайдеров"""

    SYSTEM_PROMPT_RU = """Ты — дружелюбный и опытный преподаватель Python для начинающих.
Правила:
- Отвечай на русском языке
- Объясняй просто, с примерами
- Не решай задания полностью — давай подсказки и направляй
- Если видишь ошибку — объясни причину и как исправить
- Будь мотивирующим
- Код оформляй в markdown-блоках ```python
"""

    SYSTEM_PROMPT_EN = """You are a friendly and experienced Python teacher for beginners.
Rules:
- Answer in English
- Explain simply with examples
- Do not solve tasks completely — give hints and guide
- If you see an error — explain the cause and how to fix it
- Be motivating
- Format code in markdown blocks ```python
"""

    def __init__(self, settings_manager=None):
        self.settings = settings_manager
        self.history: List[Dict] = []
        self.max_history = 20
        self._lock = threading.Lock()
        self._stop_generation = False  # Флаг для остановки генерации
        self._stream_callback = None  # Callback для потоковой передачи

        self.groq_key = self._get("ai_groq_key", "")
        self.gemini_key = self._get("ai_gemini_key", "")
        self.preferred = self._get("ai_provider", "auto")  # По умолчанию auto

        self.groq_model = "llama-3.3-70b-versatile"
        self.gemini_model = "gemini-2.5-flash"

        # Загружаем историю из файла
        self._load_history()

    def _get(self, key, default=""):
        if self.settings:
            data = self.settings.load()
            return data.get(key, default)
        return default

    def reload_keys(self):
        self.groq_key = self._get("ai_groq_key", "")
        self.gemini_key = self._get("ai_gemini_key", "")
        self.preferred = self._get("ai_provider", "groq")

    def set_keys(self, groq_key: str = None, gemini_key: str = None, provider: str = None):
        data = self.settings.load() if self.settings else {}
        if groq_key is not None:
            self.groq_key = groq_key.strip()
            data["ai_groq_key"] = self.groq_key
        if gemini_key is not None:
            self.gemini_key = gemini_key.strip()
            data["ai_gemini_key"] = self.gemini_key
        if provider in ("groq", "gemini", "auto"):
            self.preferred = provider
            data["ai_provider"] = provider
        if self.settings:
            self.settings.save(data)

    def clear_history(self):
        with self._lock:
            self.history.clear()
        self._save_history()

    def _get_history_file(self):
        """Возвращает путь к файлу истории"""
        # Сохраняем в директории приложения
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_dir, "ai_chat_history.json")

    def _load_history(self):
        """Загружает историю из файла"""
        try:
            history_file = self._get_history_file()
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                print(f"[AI Agent] Loaded {len(self.history)} messages from history")
        except Exception as e:
            print(f"[AI Agent] Error loading history: {e}")
            self.history = []

    def _save_history(self):
        """Сохраняет историю в файл"""
        try:
            history_file = self._get_history_file()
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            print(f"[AI Agent] Saved {len(self.history)} messages to history")
        except Exception as e:
            print(f"[AI Agent] Error saving history: {e}")

    def stop_generation(self):
        """Останавливает текущую генерацию"""
        self._stop_generation = True
        print("[AI Agent] Generation stopped by user")

    def _build_messages(self, user_message: str, context: str = "", locale: str = "ru") -> List[Dict]:
        system = self.SYSTEM_PROMPT_RU if locale == "ru" else self.SYSTEM_PROMPT_EN
        if context:
            context_label = "Контекст (код / урок / ошибка):" if locale == "ru" else "Context (code / lesson / error):"
            system += f"\n\n{context_label}\n{context[:3000]}"

        messages = [{"role": "system", "content": system}]
        with self._lock:
            messages.extend(self.history[-self.max_history:])
        messages.append({"role": "user", "content": user_message})
        return messages

    def _call_groq(self, messages: List[Dict]) -> str:
        if not self.groq_key:
            raise ValueError("Groq API key is not set")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 4096,  # Увеличено с 1024 до 4096 для более полных ответов
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=35)
        resp.raise_for_status()

        data = resp.json()

        # Улучшенная обработка ответа с логированием
        try:
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()
                elif "text" in choice:
                    return choice["text"].strip()
            elif "text" in data:
                return data["text"].strip()

            # Если ничего не сработало, возвращаем весь ответ для отладки
            print(f"Groq response structure: {data}")
            return str(data)

        except (KeyError, IndexError) as e:
            print(f"Error parsing Groq response: {e}")
            print(f"Response data: {data}")
            raise ValueError(f"Could not parse Groq response: {e}")

    def _call_groq_stream(self, messages: List[Dict], stream_callback: Callable[[str], None]) -> str:
        """Потоковая передача от Groq"""
        if not self.groq_key:
            raise ValueError("Groq API key is not set")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 4096,
            "stream": True  # Включаем потоковую передачу
        }

        full_response = ""
        self._stop_generation = False

        try:
            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=35)
            resp.raise_for_status()

            for line in resp.iter_lines():
                if self._stop_generation:
                    print("[AI Agent] Streaming stopped")
                    break

                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # Убираем 'data: '
                        if data_str == '[DONE]':
                            break

                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_response += content
                                    # Вызываем callback для каждого кусочка текста
                                    if stream_callback:
                                        stream_callback(content)
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            if not self._stop_generation:
                raise e

        return full_response

    def _call_gemini(self, messages: List[Dict]) -> str:
        if not self.gemini_key:
            raise ValueError("Gemini API key is not set")

        system_text = ""
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent?key={self.gemini_key}"
        )
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_text}]},
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 4096},  # Увеличено с 1024 до 4096
        }
        print(f"[AI Agent] Calling Gemini with model: {self.gemini_model}")
        print(f"[AI Agent] Gemini key length: {len(self.gemini_key)}")
        resp = requests.post(url, json=payload, timeout=35)
        resp.raise_for_status()
        
        data = resp.json()
        
        # Улучшенная обработка ответа с логированием
        try:
            # Проверяем разные возможные структуры ответа
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"].strip()
                    elif len(parts) > 0:
                        # Если текста нет, но есть другие данные
                        return str(parts[0])
                elif "text" in candidate:
                    return candidate["text"].strip()
            elif "text" in data:
                return data["text"].strip()
            
            # Если ничего не сработало, возвращаем весь ответ для отладки
            print(f"Gemini response structure: {data}")
            return str(data)
            
        except (KeyError, IndexError) as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Response data: {data}")
            raise ValueError(f"Could not parse Gemini response: {e}")

    def ask(
        self,
        user_message: str,
        context: str = "",
        locale: str = "ru",
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ):
        def worker():
            try:
                if not requests:
                    raise RuntimeError("Библиотека requests не установлена")

                messages = self._build_messages(user_message, context, locale)
                answer = None
                last_error = None

                # Умный выбор провайдера
                if self.preferred == "auto":
                    # Автоматический выбор по наличию ключей
                    if self.groq_key and self.gemini_key:
                        order = ["groq", "gemini"]  # Groq предпочтительнее (быстрее)
                    elif self.groq_key:
                        order = ["groq"]
                    elif self.gemini_key:
                        order = ["gemini"]
                    else:
                        order = []
                elif self.preferred == "groq":
                    order = ["groq", "gemini"] if self.gemini_key else ["groq"]
                elif self.preferred == "gemini":
                    order = ["gemini", "groq"] if self.groq_key else ["gemini"]
                else:
                    order = ["groq", "gemini"]

                print(f"[AI Agent] Using provider order: {order}")
                print(f"[AI Agent] User message: {user_message[:100]}...")

                for provider in order:
                    try:
                        print(f"[AI Agent] Trying provider: {provider}")
                        if provider == "groq" and self.groq_key:
                            if stream and stream_callback:
                                # Используем потоковую передачу
                                answer = self._call_groq_stream(messages, stream_callback)
                            else:
                                answer = self._call_groq(messages)
                            print(f"[AI Agent] Groq answer received: {answer[:100] if answer else 'None'}...")
                            break
                        if provider == "gemini" and self.gemini_key:
                            answer = self._call_gemini(messages)
                            print(f"[AI Agent] Gemini answer received: {answer[:100] if answer else 'None'}...")
                            break
                    except Exception as e:
                        last_error = str(e)
                        print(f"[AI Agent] Provider {provider} failed: {e}")
                        continue

                if answer is None:
                    raise RuntimeError(
                        last_error or "Нет API-ключей или оба провайдера недоступны"
                    )

                print(f"[AI Agent] Final answer: {answer[:100] if answer else 'None'}...")

                with self._lock:
                    self.history.append({"role": "user", "content": user_message})
                    self.history.append({"role": "assistant", "content": answer})
                    # Сохраняем историю в файл
                    self._save_history()

                if on_success:
                    print(f"[AI Agent] Calling on_success with answer length: {len(answer) if answer else 0}")
                    Clock.schedule_once(lambda dt: on_success(answer), 0)
            except Exception as e:
                error_msg = str(e)
                # Скрываем API ключ из сообщения об ошибке
                import re
                error_msg = re.sub(r'key=[A-Za-z0-9\-_\.]+', 'key=***', error_msg)
                print(f"[AI Agent] Error in ask: {error_msg}")
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(error_msg), 0)

        threading.Thread(target=worker, daemon=True).start()

    def explain_error(self, error_text: str, code: str = "", locale: str = "ru", **kwargs):
        prompt = (
            f"Объясни эту ошибку Python простым языком и скажи, как её исправить:\n\n{error_text}"
        )
        context = f"Код пользователя:\n```python\n{code}\n```" if code else ""
        self.ask(prompt, context=context, locale=locale, **kwargs)

    def review_code(self, code: str, locale: str = "ru", **kwargs):
        prompt = "Проверь этот код Python. Укажи ошибки, возможные улучшения и кратко объясни, что делает код."
        self.ask(prompt, context=f"```python\n{code}\n```", locale=locale, **kwargs)

    def lesson_hint(self, task: str, current_code: str, theory: str = "", locale: str = "ru", **kwargs):
        prompt = "Дай полезную подсказку по этому заданию (не решай полностью)."
        context = (
            f"Задание:\n{task}\n\nТеория:\n{theory[:1500]}\n\n"
            f"Текущий код ученика:\n```python\n{current_code}\n```"
        )
        self.ask(prompt, context=context, locale=locale, **kwargs)
