# upgrade_kb.py
import json

# Загружаем текущую базу
with open("knowledge_base.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Сопоставим completion → prompt для FAQ из исходных файлов
faq_mapping = {}

# Собираем все исходные JSONL-файлы
import os
jsonl_files = ["Qwen_json_20251124_zp3mexqll.txt", "Qwen_json_20251124_ifdpnnpy1.txt"]
for fname in jsonl_files:
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    faq_mapping[item["completion"]] = item["prompt"]

# Обновляем записи типа "faq"
updated = 0
for item in data:
    if item["type"] == "faq":
        if item["text"] in faq_mapping:
            prompt = faq_mapping[item["text"]]
            item["text"] = f"Вопрос: {prompt}\nОтвет: {item['text']}"
            updated += 1

# Сохраняем
with open("knowledge_base_enhanced.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Обновлено {updated} FAQ. Новый файл: knowledge_base_enhanced.json")
