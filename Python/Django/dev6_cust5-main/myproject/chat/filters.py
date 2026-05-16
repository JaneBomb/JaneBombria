BANNED_WORDS = [
    "badword1",
    "badword2",
]


def filter_message(content):
    for word in BANNED_WORDS:
        content = content.replace(word, "0" * len(word))
    return content
