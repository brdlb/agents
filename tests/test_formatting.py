from src.utils.formatting import markdown_to_html

def test_markdown_to_html_basic():
    print(f"Bold: {markdown_to_html('**bold**')}")
    assert markdown_to_html("**bold**") == "<b>bold</b>"
    print(f"Italic: {markdown_to_html('*italic*')}")
    assert markdown_to_html("*italic*") == "<i>italic</i>"
    print(f"Code: {markdown_to_html('`code`')}")
    assert markdown_to_html("`code`") == "<code>code</code>"
    print(f"Link: {markdown_to_html('[link](http://example.com)')}")
    assert markdown_to_html("[link](http://example.com)") == '<a href="http://example.com">link</a>'

def test_markdown_to_html_nested():
    print(f"Nested: {markdown_to_html('**bold *italic***')}")
    assert markdown_to_html("**bold *italic***") == "<b>bold <i>italic</i></b>"

def test_markdown_to_html_code_blocks():
    text = "```python\nprint('hello')\n```"
    expected = "<pre><code class=\"language-python\">print(&#x27;hello&#x27;)</code></pre>"
    actual = markdown_to_html(text)
    print(f"Code block: '{actual}'")
    assert actual == expected

def test_markdown_to_html_escaping():
    # Тест экранирования символов, которые не в Markdown
    assert markdown_to_html("1 < 2 & 3 > 2") == "1 &lt; 2 &amp; 3 &gt; 2"
    # Тест экранирования внутри кода
    assert markdown_to_html("`a < b`") == "<code>a &lt; b</code>"

def test_markdown_to_html_headers():
    assert markdown_to_html("# Header 1") == "<b>Header 1</b>"
    assert markdown_to_html("## Header 2") == "<b>Header 2</b>"

def test_markdown_to_html_multiline_quotes():
    text = "> Line 1\n> Line 2"
    # Наш текущий regex заменит каждую строку по отдельности
    expected = "<blockquote>Line 1</blockquote>\n<blockquote>Line 2</blockquote>"
    assert markdown_to_html(text) == expected

if __name__ == "__main__":
    try:
        test_markdown_to_html_basic()
        test_markdown_to_html_nested()
        test_markdown_to_html_code_blocks()
        test_markdown_to_html_escaping()
        test_markdown_to_html_headers()
        test_markdown_to_html_multiline_quotes()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
