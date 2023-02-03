from typing import Optional

from pydantic import validator

from meerkat.interactive.app.src.lib.component.abstract import Component


class Markdown(Component):

    """
    Render markdown with GitHub Flavored Markdown (GFM) syntax.

    The implementation of this component uses the marked.js library (https://github.com/markedjs/marked).
    Argument descriptions below are taken directly from the marked.js documentation.

    Args:
        body: The markdown data to render.
        classes: The Tailwind classes to apply to the component, see @tailwindcss/typography \
            for the classes that are specifically available to style this component.
        baseUrl: The base URL to use for relative links.
        breaks: If true, add <br> on a single line break (copies GitHub behavior on comments, 
            but not on rendered markdown files). Requires gfm be true.
        gfm: If true, use approved GitHub Flavored Markdown (GFM) specification.
        headerIds: If true, include an id attribute when emitting headings (h1, h2, h3, etc).
        headerPrefix: A string to prefix the id attribute when emitting headings (h1, h2, h3, etc).
        langPrefix: A string to prefix the className in a <code> block. Useful for syntax highlighting.
        mangle: If true, autolinked email address is escaped with HTML character references.
        pedantic: If true, conform to the original markdown.pl as much as possible. Don't fix original 
            markdown bugs or behavior. Turns off and overrides gfm.
        sanitize: If true, sanitize the HTML passed into markdownString with the sanitizer function.
        silent: If true, the parser does not throw any exception.
        smartypants: If true, use "smart" typographic punctuation for things like quotes and dashes.
        xhtml: If true, emit self-closing HTML tags for void elements (<br/>, <img/>, etc.) with a "/" 
            as required by XHTML.
    """

    body: str
    classes: str = ""
    baseUrl: Optional[str] = None
    breaks: bool = True
    gfm: bool = True
    headerIds: bool = True
    headerPrefix: str = ""
    langPrefix: str = "language-"
    mangle: bool = True
    pedantic: bool = False
    sanitize: bool = False
    silent: bool = False
    smartypants: bool = False
    xhtml: bool = False


class Title(Markdown):
    """
    Display title text.

    Use this component for the main title of a page.
    This will place the text in an `<h1>` tag.
    """

    @validator("body", pre=True)
    def make_title(cls, v):
        return f"# {v}"


class Header(Markdown):
    """
    Display header text.

    Use this component for the main header of a section.
    This will place the text in an `<h2>` tag.
    """

    @validator("body", pre=True)
    def make_header(cls, v):
        return f"## {v}"


class Subheader(Markdown):
    """
    Display subheader text.

    Use this component for the subheader of a section.
    This will place the text in an `<h3>` tag.
    """

    @validator("body", pre=True)
    def make_subheader(cls, v):
        return f"### {v}"


class Caption(Markdown):
    """
    Display caption text in a smaller, gray font size.

    Use this component for explanatory text that is not the main body of a section.
    This will place the text in a `<p>` tag.

    Default Tailwind classes:
        text-sm text-gray-400
    """

    @validator("classes", pre=True, always=True)
    def add_classes(cls, v):
        classes = "text-sm text-gray-400"
        return classes if v is None else f"{v} {classes}"
