from src.utils.formatting import markdown_to_html

def test_markdown_to_html_basic():
    assert markdown_to_html("**bold**") == "<b>bold</b>"
    assert markdown_to_html("*italic*") == "<i>italic</i>"
    assert markdown_to_html("`code`") == "<code>code</code>"
    assert markdown_to_html("[link](http://example.com)") == '<a href="http://example.com">link</a>'

def test_markdown_to_html_nested():
    assert markdown_to_html("**bold *italic***") == "<b>bold <i>italic</i></b>"

def test_markdown_to_html_code_blocks():
    text = "```python\nprint('hello')\n```"
    expected = "<pre><code class=\"language-python\">print(&#x27;hello&#x27;)</code></pre>"
    assert markdown_to_html(text) == expected

def test_markdown_to_html_escaping():
    assert markdown_to_html("1 < 2 & 3 > 2") == "1 &lt; 2 &amp; 3 &gt; 2"
    assert markdown_to_html("`a < b`") == "<code>a &lt; b</code>"

def test_markdown_to_html_headers():
    assert markdown_to_html("# Header 1") == "<b>Header 1</b>"
    assert markdown_to_html("## Header 2") == "<b>Header 2</b>"

def test_markdown_to_html_multiline_quotes():
    text = "> Line 1\n> Line 2"
    expected = "<blockquote>Line 1</blockquote>\n<blockquote>Line 2</blockquote>"
    assert markdown_to_html(text) == expected

if __name__ == "__main__":
    test_markdown_to_html_basic()
    test_markdown_to_html_nested()
    test_markdown_to_html_code_blocks()
    test_markdown_to_html_escaping()
    test_markdown_to_html_headers()
    test_markdown_to_html_multiline_quotes()
    print("All tests passed!")
