# prepare_data.py
import json
import os
import re

INPUT_JSONL = [
    "Qwen_json_20251124_zp3mexqll.txt",
    "Qwen_json_20251124_ifdpnnpy1.txt",
    "Qwen_json_20251124_dnsp4l0fa.txt"
]

INPUT_JSON_ARRAY = "Qwen_json_20251124_xq9seoj9d.txt"
OUTPUT_FILE = "knowledge_base.json"

def load_json_array(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped == "":
            continue
        clean_lines.append(line)

    content = "".join(clean_lines)
    content = re.sub(r',\s*]', ']', content)  # удаляем запятую перед ]
    data = json.loads(content)
    return [item for item in data if item.get("type") != "law_obsolete"]

def load_jsonl(file_path):
    docs = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if "completion" not in item or "prompt" not in item:
                    print(f"⚠️ Пропущена строка {line_num} в {file_path}: нет 'prompt' или 'completion'")
                    continue
                docs.append(item)
            except json.JSONDecodeError as e:
                print(f"⚠️ Ошибка JSON в строке {line_num} файла {file_path}: {e}")
                continue
    return docs

def determine_source(prompt, text, filename):
    if "Торги РФ" in text or "rftorgi" in text or "ООО «Электронные торговые системы качества»" in text:
        return "ЭТП «Торги РФ» и методические материалы"

    mapping = {
        "Какие организации подпадают под действие Федерального закона №223-ФЗ?": "ФЗ-223, ст. 1–2",
        "В чём основное отличие 223-ФЗ от 44-ФЗ?": "Методические рекомендации Минэкономразвития",
        "Что такое Положение о закупках по 223-ФЗ?": "ФЗ-223, ст. 3–4",
        "Какие основные этапы закупочного цикла по 223-ФЗ?": "ФЗ-223, ст. 3–13",
        "Обязательна ли публикация закупок в ЕИС по 223-ФЗ?": "ФЗ-223, ст. 21; Постановление №1352",
        "Какие формы закупок разрешены по 223-ФЗ?": "ФЗ-223, ст. 6–7",
        "Когда закупка по 223-ФЗ должна проводиться в электронной форме?": "ФЗ-223, ст. 15",
        "Какие требования предъявляются к участникам закупок по 223-ФЗ?": "ФЗ-223, ст. 8",
        "Что такое машиночитаемая доверенность (МЧД) и где она используется?": "Приказ Минцифры №858; ФЗ-223",
        "Как подаётся заявка на участие в электронной закупке по 223-ФЗ?": "ФЗ-223, ст. 9, 15",
        "Что такое обеспечение заявки и для чего оно нужно?": "ФЗ-223, ст. 9",
        "Как проводится рассмотрение заявок по 223-ФЗ?": "ФЗ-223, ст. 9, 12",
        "Что такое переторжка и как она проводится?": "ФЗ-223, ст. 9",
        "Какие ограничения введены по национальному режиму в 223-ФЗ с 2025 года?": "ФЗ-223, ст. 31",
        "Какие отчёты обязан размещать заказчик по 223-ФЗ?": "ФЗ-223, ст. 21",
        "Как отменить закупку по 223-ФЗ?": "ФЗ-223, ст. 11",
        "Что такое РНП и как туда попасть?": "ФЗ-223, ст. 25; КоАП РФ",
        "Обязан ли заказчик по 223-ФЗ заключать договор с победителем?": "ФЗ-223, ст. 13",
        "Как проверить, включена ли ЭТП в реестр Минцифры?": "ФЗ-223, ст. 19; сайт Минцифры России",
        "Какие штрафы предусмотрены за нарушение 223-ФЗ?": "ФЗ-223, ст. 27; КоАП РФ"
    }
    return mapping.get(prompt, "ФЗ-223 и подзаконные акты")

def main():
    all_docs = []

    # 1. Основной JSON-массив
    if os.path.exists(INPUT_JSON_ARRAY):
        print("✅ Загружаем основной массив (статьи закона и подзаконные акты)...")
        law_docs = load_json_array(INPUT_JSON_ARRAY)
        all_docs.extend(law_docs)

    # 2. JSONL файлы
    seen_texts = set(doc["text"] for doc in all_docs)

    for filename in INPUT_JSONL:
        if not os.path.exists(filename):
            print(f"⚠️ Файл {filename} не найден — пропускаем.")
            continue

        print(f"✅ Обрабатываем {filename}...")
        items = load_jsonl(filename)
        for item in items:
            text = item["completion"]
            if text in seen_texts:
                continue
            seen_texts.add(text)

            source = determine_source(item["prompt"], text, filename)
            all_docs.append({
                "id": f"{filename}_{len(all_docs)}",
                "text": text,
                "source": source,
                "type": "faq",
                "tags": ["ЭТП", "процедуры", "Торги РФ"] if "Торги РФ" in text else ["223-ФЗ", "практика"]
            })

    # Сохраняем
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Готово! База знаний сохранена в {OUTPUT_FILE}")
    print(f"Всего записей: {len(all_docs)}")

if __name__ == "__main__":
    main()
