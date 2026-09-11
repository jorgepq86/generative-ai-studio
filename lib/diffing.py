import difflib
import html


def word_diff_html(old_text, new_text):
    """Render a word-level diff between two texts as HTML."""
    old_words = (old_text or "").split()
    new_words = (new_text or "").split()

    matcher = difflib.SequenceMatcher(a=old_words, b=new_words)
    parts = []
    for opcode, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if opcode == "equal":
            parts.extend(html.escape(word) for word in new_words[b_start:b_end])
        else:
            if opcode in ("delete", "replace"):
                for word in old_words[a_start:a_end]:
                    parts.append(
                        '<span style="background-color:rgba(248,80,80,0.25); '
                        'text-decoration:line-through;">' + html.escape(word) + "</span>"
                    )
            if opcode in ("insert", "replace"):
                for word in new_words[b_start:b_end]:
                    parts.append(
                        '<span style="background-color:rgba(80,200,80,0.25);">'
                        + html.escape(word) + "</span>"
                    )

    return " ".join(parts)
