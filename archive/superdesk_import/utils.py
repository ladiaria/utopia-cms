import traceback
from markdownify import MarkdownConverter, markdownify as md


class ImageBlockConverter(MarkdownConverter):
    """
    Create a custom MarkdownConverter that adds two newlines after an image
    """
    def convert_img(self, el, text, convert_as_inline):
        return super().convert_img(el, text, convert_as_inline) + '\n\n'


def html_to_markdown(html_string):
    try:
        return md(html_string) if html_string else ''
    except Exception as ex:
        print(str(ex), traceback.format_exc())
        raise
