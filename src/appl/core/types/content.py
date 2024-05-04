from typing import Optional

from pydantic import BaseModel, Field

from .basic import *
from .futures import String, is_string


class Image(BaseModel):
    """Represent an image in the message."""

    url: str = Field(..., description="The URL of the image")
    detail: Optional[str] = Field(
        None, description="Specifies the detail level of the image."
    )

    def __init__(self, url: str, detail: Optional[str] = None) -> None:
        """Initialize the image with the URL and detail level.

        See [the guide](https://platform.openai.com/docs/guides/vision/low-or-high-fidelity-image-understanding)
        for more information about the detail level.
        """
        super().__init__(url=url, detail=detail)

    def __repr__(self) -> str:
        return f"Image(url={self.url})"

    def __str__(self) -> str:
        return f"[Image]{self.url}"


StrOrImg = Union[String, Image]
"""A type that can be either a string or an image."""


class ContentList(BaseModel):
    """Represent a list of contents containing text and images."""

    contents: List[StrOrImg] = Field(..., description="The content of the message")

    def __iadd__(
        self, other: Union[StrOrImg, List[StrOrImg], "ContentList"]
    ) -> "ContentList":
        if isinstance(other, ContentList):
            self.extend(other.contents)
        elif isinstance(other, list):
            self.extend(other)
        else:
            self.append(other)
        return self

    def append(self, content: StrOrImg) -> None:
        """Append a content to the list.

        If the last content is a string, it will be concatenated with the new content.
        """
        if is_string(content) and len(self.contents) and is_string(self.contents[-1]):
            self.contents[-1] += content  # type: ignore
        else:
            self.contents.append(content)

    def extend(self, contents: list[StrOrImg]) -> None:
        """Extend the list with multiple contents."""
        for content in contents:
            self.append(content)

    def get_contents(self) -> List[Dict[str, Any]]:
        """Return the contents as a list of dictionaries."""

        def get_dict(content):
            if isinstance(content, Image):
                image_args = {"url": content.url}
                if content.detail:
                    image_args["detail"] = content.detail
                return {"type": "image_url", "image_url": image_args}
            return {"type": "text", "text": str(content)}

        return [get_dict(c) for c in self.contents]

    def __str__(self) -> str:
        return "\n".join([str(c) for c in self.contents])
