import re
import html
from typing import Dict

def markdown_to_html(text: str) -> str:
    """
    Конвертирует базовый Markdown в HTML, поддерживаемый Telegram.
    """
    if not text:
        return ""

    # Хранилище для блоков кода
    code_blocks: Dict[str, str] = {}
    block_counter = 0

    def save_block(match):
        nonlocal block_counter
        placeholder = f"MARKDOWNBLOCK{block_counter}END"
        lang = match.group(1) or ""
        code = match.group(2)
        escaped_code = html.escape(code)
        if lang:
            code_blocks[placeholder] = f'<pre><code class="language-{lang}">{escaped_code}</code></pre>'
        else:
            code_blocks[placeholder] = f'<pre>{escaped_code}</pre>'
        block_counter += 1
        return placeholder

    def save_inline(match):
        nonlocal block_counter
        placeholder = f"MARKDOWNINLINE{block_counter}END"
        code = match.group(1)
        escaped_code = html.escape(code)
        code_blocks[placeholder] = f'<code>{escaped_code}</code>'
        block_counter += 1
        return placeholder

    # 1. Сохраняем блоки кода
    # Улучшенный regex для корректного захвата кода без лишних переводов строк в конце
    text = re.sub(r'```(\w*)\n?(.*?)\n?```', save_block, text, flags=re.DOTALL)
    
    # 2. Сохраняем инлайновый код
    text = re.sub(r'`([^`\n]+)`', save_inline, text)

    # 3. Экранируем HTML-спецсимволы
    text = html.escape(text, quote=False)

    # 4. Обрабатываем жирный+курсив (***text***)
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)

    # 5. Обрабатываем жирный (**text**, __text__)
    text = re.sub(r'\*\*(.*?)\*\*(?!\*)', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__(?!_)', r'<b>\1</b>', text)

    # 6. Обрабатываем курсив (*text*, _text_)
    text = re.sub(r'\*(.*?)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_(?!_)', r'<i>\1</i>', text)

    # 7. Обрабатываем ссылки
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)

    # 8. Обрабатываем заголовки
    text = re.sub(r'^#+\s+(.*?)$', r'<b>\1</b>', text, flags=re.M)

    # 9. Обрабатываем цитаты
    text = re.sub(r'^>\s+(.*?)$', r'<blockquote>\1</blockquote>', text, flags=re.M)

    # 10. Возвращаем блоки кода
    for placeholder, code_html in code_blocks.items():
        text = text.replace(placeholder, code_html)

    return text
