from lib.diffing import word_diff_html


def test_identical_texts_produce_no_additions_or_deletions():
    text = "El zorro marrón salta sobre el perro perezoso"
    result = word_diff_html(text, text)
    assert "line-through" not in result
    assert "background-color:rgba(80,200,80" not in result
    for word in text.split():
        assert word in result


def test_changed_word_shows_both_old_and_new():
    old_text = "El texto original es bueno"
    new_text = "El texto revisado es bueno"
    result = word_diff_html(old_text, new_text)
    assert "original" in result
    assert "revisado" in result
    assert "line-through" in result
    assert "background-color:rgba(80,200,80" in result


def test_does_not_crash_on_empty_strings():
    assert word_diff_html("", "") == ""
    assert word_diff_html("", "texto nuevo") != ""
    assert word_diff_html("texto viejo", "") != ""
    assert word_diff_html(None, None) == ""
