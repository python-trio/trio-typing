import trio
import ssl
from typing import Optional, Tuple, List

class SSLStream(trio.abc.Stream):
    transport_stream: trio.abc.Stream
    context: ssl.SSLContext
    server_side: bool
    server_hostname: Optional[str]
    session: Optional[ssl.SSLSession]
    session_reused: bool

    def __init__(
        self,
        transport_stream: trio.abc.Stream,
        ssl_context: ssl.SSLContext,
        *,
        server_hostname: Optional[str] = None,
        server_side: bool = False,
        https_compatible: bool = False,
        max_refill_bytes: int = ...,
    ) -> None: ...

    def getpeercert(self, binary_form: bool = ...) -> ssl._PeerCertRetType: ...
    def selected_npn_protocol(self) -> Optional[str]: ...
    def selected_alpn_protocol(self) -> Optional[str]: ...
    def cipher(self) -> Tuple[str, int, int]: ...
    def shared_ciphers(self) -> Optional[List[Tuple[str, int, int]]]: ...
    def compression(self) -> Optional[str]: ...
    def pending(self) -> int: ...
    def get_channel_binding(self, cb_type: str = ...) -> Optional[bytes]: ...

    async def do_handshake(self) -> None: ...
    async def unwrap(self) -> Tuple[trio.abc.Stream, bytes]: ...

class SSLListener(trio.abc.Listener[SSLStream]):
    transport_listener: trio.abc.Listener

    def __init__(
        self,
        transport_listener: trio.abc.Listener,
        ssl_context: ssl.SSLContext,
        *,
        https_compatible: bool = False,
        max_refill_bytes: int = ...,
    ) -> None: ...
