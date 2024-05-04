from .basic import *


class FutureValue(ABC):
    """Represents a value that may not be ready yet."""

    @abstractmethod
    def _get_val(self):
        """Get the value of the future.

        If the future is not ready, it will block until the value is ready.
        """
        raise NotImplementedError

    @property
    def val(self):
        """The value of the future."""
        return self._get_val()

    def __call__(self):
        """Use call to get the value of the future."""
        return self.val


class CallFuture(FutureValue):
    """Represent a function call that may not be ready yet."""

    def __init__(
        self,
        func: Callable,
        *args: Any,
        use_process: bool = False,
        lazy_eval: bool = False,
        **kwargs: Any,
    ):
        """Initialize the CallFuture.

        Args:
            func: The function to call.
            *args: The arguments of the function.
            use_process: Whether to use a process pool executor.
            lazy_eval: Whether to delay the start of the call until needed.
            **kwargs: The keyword arguments of the function.
        """
        # TODO: maybe use a global executor from the config
        self._executor = (
            ProcessPoolExecutor(max_workers=1)
            if use_process
            else ThreadPoolExecutor(max_workers=1)
        )
        self._submit_fn = lambda: self._executor.submit(func, *args, **kwargs)
        self._submitted = False
        self._info = func.__name__
        # self._debug = False
        # if self._debug:
        #     # arg and kwargs might contains future objects
        #     args_list = [f"{arg}" for arg in args] + [
        #         f"{k}={v!r}" for k, v in kwargs.items()
        #     ]
        #     args_str = ", ".join(args_list)
        #     self._info += f"({args_str})"
        if not lazy_eval:
            # delay the start of the call until needed
            self._submit()

    def _submit(self) -> None:
        if not self._submitted:
            self._future: Future = self._submit_fn()
            self._submitted = True

    @property
    def future(self):
        """The future object of the call."""
        if not self._submitted:
            self._submit()
        return self._future

    def result(self) -> Any:
        """Get the result of the call."""
        # This will block until the result is available
        return self.future.result()

    def cancel(self) -> bool:
        """Cancel the call."""
        # Attempt to cancel the call
        return self.future.cancel()

    def done(self) -> bool:
        """Check if the call has completed."""
        # Check if the future has completed
        return self.future.done()

    def _get_val(self):
        return self.result()

    def __str__(self):
        return str(self.val)

    def __repr__(self):
        return repr(self.future)


# TODO: boolean future
class CmpStringFuture(FutureValue):
    """Represent a comparison between a StringFuture and another value."""

    def __init__(
        self, a: "StringFuture", b: "StringFuture", op: Callable[[str, str], bool]
    ):
        """Initialize the CmpStringFuture."""
        self._a = a
        self._b = b
        self._op = op

    def __bool__(self):
        return self._op(str(self._a), str(self._b))

    def _get_val(self):
        return self.__bool__()


class StringFuture(FutureValue, BaseModel):
    """StringFuture is a string that may not be ready yet."""

    s: List[Any] = Field([], description="The string content")

    def __init__(self, content: Any = "", set_value: bool = False):
        """Initialize the StringFuture."""
        if set_value:
            if not isinstance(content, List):
                raise ValueError("Cannot set value to non-list.")
            s = content
        else:
            s = [content]
        super().__init__(s=s)

    @classmethod
    def from_list(cls, content: List[Any]) -> "StringFuture":
        """Create a StringFuture from a list of content."""
        return cls(content, set_value=True)

    def _collapse(self) -> str:
        return "".join([str(x) for x in self.s])

    def materialized(self) -> "StringFuture":
        """Materialize the StringFuture."""
        self.s = [self._collapse()]
        return self

    def serialize(self) -> str:
        """Serialize the StringFuture."""
        return str(self)

    def _get_val(self):
        return str(self)

    def __str__(self) -> str:
        return self.materialized().s[0]

    def __hash__(self) -> int:
        return hash(str(self))

    def __contains__(self, item: str) -> bool:
        return item in str(self)

    def __getattr__(self, key):
        if not hasattr(str, key):
            raise AttributeError("str has no attribute " + key)
        return getattr(str(self), key)

    def __iadd__(self, other: "String") -> "StringFuture":
        if isinstance(other, str):
            self.s.append(other)
            return self
        elif isinstance(other, StringFuture):
            self.s += other.s
            return self
        else:
            raise RuntimeError("Cannot add StringFuture to non-string.")

    def __radd__(self, other: "String") -> "StringFuture":
        if isinstance(other, str):
            return StringFuture.from_list([other] + self.s)
        else:
            raise RuntimeError("Cannot add StringFuture to non-string.")

    def __add__(self, other: "String") -> "StringFuture":
        if isinstance(other, str):
            return StringFuture.from_list(self.s + [other])
        elif isinstance(other, StringFuture):
            return StringFuture.from_list(self.s + other.s)
        else:
            raise RuntimeError("Cannot add StringFuture to non-string.")

    def __eq__(self, other: Any) -> CmpStringFuture:  # type: ignore
        return CmpStringFuture(self, other, operator.eq)

    def __ge__(self, other: Any) -> CmpStringFuture:
        return CmpStringFuture(self, other, operator.ge)

    def __gt__(self, other: Any) -> CmpStringFuture:
        return CmpStringFuture(self, other, operator.gt)

    def __le__(self, other: Any) -> CmpStringFuture:
        return CmpStringFuture(self, other, operator.le)

    def __lt__(self, other: Any) -> CmpStringFuture:
        return CmpStringFuture(self, other, operator.lt)

    def __ne__(self, other: Any) -> CmpStringFuture:  # type: ignore
        return CmpStringFuture(self, other, operator.ne)

    def __format__(self, __format_spec: str) -> str:
        return str(self).__format__(__format_spec)

    def __getitem__(self, key: Union[SupportsIndex, slice]) -> "StringFuture":
        def func():
            return str(self)[key]

        return StringFuture(CallFuture(func))

    def __deepcopy__(self, memo: Optional[Dict[int, Any]] = None) -> "StringFuture":
        # materialize before copying, to avoid functions wrapped in StringFuture running twice.
        return StringFuture(str(self))


# Type aliases
String = Union[StringFuture, str]
"""String is a type alias for StringFuture or str."""


def is_string(s: Any) -> bool:
    """Check if the object is a StringFuture or str."""
    return isinstance(s, StringFuture) or isinstance(s, str)
