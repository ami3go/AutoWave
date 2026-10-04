# AutoWave protocol API

Version 0.2.0 introduces a pure protocol layer under `autowave.protocol`.
It contains no VISA, transport, session, retry, sleep, recovery, or workflow logic.

The authoritative behavior baseline remains
[`AUTOWAVE_PROTOCOL_BASELINE.md`](AUTOWAVE_PROTOCOL_BASELINE.md).

## Layer boundary

```text
future driver/workflows
        |
transport/session executor      PR03+
        |
autowave.protocol               PR02
        |
bytes in / bytes out
```

The protocol layer is responsible only for:

- checksum calculation;
- validating framed-command payloads;
- building `STX + payload + ETX + checksum` frames;
- classifying one complete response message;
- verifying decorated response framing and checksum;
- preserving raw payload bytes;
- ASCII decoding only when the caller explicitly asks for text;
- converting NAK, NOTREADY, and BUSY classifications to typed exceptions on request.

## Constants and bounds

```python
from autowave.protocol import (
    STX,
    ETX,
    ACK,
    NAK,
    NOT_READY,
    BUSY,
    DEFAULT_MAX_COMMAND_PAYLOAD,
    DEFAULT_MAX_RESPONSE_SIZE,
)
```

Initial defensive software bounds:

- command payload: 4096 bytes;
- complete response message: 65536 bytes.

These are software safety limits, not claims about the instrument's physical maximum.

## Checksum

```python
from autowave.protocol import calculate_checksum

assert calculate_checksum(b"STAT? PSRC") == 0xD3
assert calculate_checksum(b"LCN?") == 0x3C
assert calculate_checksum(b" ") == 0x40
```

The 0x20 boundary follows the dedicated checksum section of the vendor manual and the verified
legacy implementation. Real hardware verification of that exact boundary remains in the HIL
backlog.

## Encoding framed commands

```python
from autowave.protocol import encode_command

frame = encode_command("STAT? TEST")
```

`encode_command()` accepts ASCII text only. This is deliberate: the vendor manual describes
single-byte values through 0xFF but does not define the character mapping for 0x80-0xFF.
The driver must not silently substitute UTF-8.

For callers that already possess verified single-byte payloads, `encode_frame()` accepts
`bytes` directly and preserves bytes from 0x20 through 0xFF.

Commands beginning with `*` are rejected by the framed encoder. The vendor protocol defines
those commands as permanently unframed, even after protocol mode is enabled.

## Parsing replies

```python
from autowave.protocol import AutoWaveReplyKind, parse_reply

reply = parse_reply(raw_message)

if reply.kind is AutoWaveReplyKind.DATA:
    payload = reply.payload
```

`parse_reply()` expects exactly one complete response message, normally supplied by the
bounded GPIB backend-message/EOI read that will be implemented in PR03.

Possible kinds:

| Kind | Wire form | Meaning |
| --- | --- | --- |
| `ACK` | `0x06` | command accepted/completed |
| `NAK` | `0x15` | command/checksum rejected |
| `NOT_READY` | `0x16` | command not accepted because device is not ready |
| `BUSY` | `0x19` | device requires exact-message re-query |
| `DATA` | decorated frame | validated payload bytes |

The parser does not retry anything.

## Status-to-exception conversion

```python
from autowave.protocol import parse_reply, raise_for_status

reply = raise_for_status(parse_reply(raw_message))
```

`raise_for_status()` maps:

- NAK -> `AutoWaveNakError`
- NOTREADY -> `AutoWaveNotReadyError`
- BUSY -> `AutoWaveBusyError`

ACK and DATA pass through unchanged.

BUSY being represented as a typed status error does **not** authorize generic retry. PR03 is
responsible for the separately bounded vendor-defined exact-message BUSY loop.

## Text decoding

```python
from autowave.protocol import decode_payload_text

text = decode_payload_text(reply)
```

The parser always preserves the original bytes. `decode_payload_text()` only accepts a DATA
reply and decodes strict ASCII. Non-ASCII payloads remain available as bytes until the vendor
code page is verified.

## Error hierarchy

All AutoWave errors derive from `AutoWaveError` and also integrate with the appropriate
`scpi-driver-core` category:

```text
ScpiDriverError
  |
  +-- AutoWaveError
        |
        +-- AutoWaveValidationError   (also ConfigurationError)
        +-- AutoWaveProtocolError     (also ProtocolError)
              |
              +-- AutoWaveResponseError
                    |
                    +-- AutoWaveChecksumError
                    +-- AutoWaveNakError
                    +-- AutoWaveNotReadyError
                    +-- AutoWaveBusyError
```

This allows callers to catch either the concrete device error or a shared core category.

## Explicit non-goals of PR02

The protocol module does not:

- open or close a VISA resource;
- discover instruments;
- send `*IDN?`;
- enable `*PRCL:ON`;
- sleep for 250 ms;
- retry BUSY;
- recover a faulted session;
- decide whether an operation is safe to replay;
- manipulate voltage, trigger, generator mode, files, or tests.

Those responsibilities remain in later reviewed layers.
