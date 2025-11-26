# bot.py
import json
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
import ollama
from dotenv import load_dotenv
import os

# === НАСТРОЙКИ ===
load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
KNOWLEDGE_FILE = "knowledge_base.json"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "fz223_rag"

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(level=logging.INFO)

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Загрузка знаний
with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
    docs = json.load(f)

# Векторная БД
client = chromadb.PersistentClient(path=CHROMA_PATH)
embedding_func = SentenceTransformerEmbeddingFunction(
    model_name="intfloat/multilingual-e5-large-instruct"
)

try:
    collection = client.get_collection(COLLECTION_NAME)
    logging.info("✅ Коллекция уже существует")
except:
    logging.info("🔄 Создаём векторную базу...")
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_func
    )
    collection.add(
        ids=[str(i) for i in range(len(docs))],
        documents=[d["text"] for d in docs],
        metadatas=[{"source": d["source"]} for d in docs]
    )
    logging.info("✅ Векторная база создана")

# Поиск релевантных фрагментов
def retrieve_context(query: str, n=7):
    results = collection.query(query_texts=[query], n_results=n)
    return [
        {"text": doc, "source": meta.get("source", "не указан")}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

# Генерация ответа
def generate_answer(question: str, context_items):
    context_str = "\n".join(
        f"{i+1}. {item['text']} (Источник: {item['source']})"
        for i, item in enumerate(context_items)
    )

    prompt = f"""Ты — эксперт по ЭТП «Торги РФ» и 223-ФЗ.
Отвечай кратко, точно и на основе контекста. Если контекст косвенно релевантен — используй его для ответа.
Если точного совпадения нет — скажи: «По доступным данным: [краткий вывод]». Не придумывай.

Вопрос: {question}

Контекст (топ-релевантные фрагменты):
{context_str}

Ответ:"""

    response = ollama.chat(
        model="qwen2:7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1}
    )
    answer = response["message"]["content"].strip()

    # Добавляем источники, если модель их не включила
    if "Источник:" not in answer and context_items:
        sources = list(set(item["source"] for item in context_items))
        if sources:
            answer += f"\n\nИсточники:\n" + "\n".join(f"- {s}" for s in sources)

    return answer

# Обработка сообщений
@dp.message(F.text)
async def handle_message(message: Message):
    try:
        user_query = message.text.strip()
        context = retrieve_context(user_query)
        answer = generate_answer(user_query, context)
        await message.answer(answer, parse_mode=None)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

# Запуск
if __name__ == "__main__":
    print("🚀 Бот запущен. Нажмите Ctrl+C для остановки.")
    dp.run_polling(bot)
