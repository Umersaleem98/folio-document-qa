"""Install official Ollama CPU runtime inside ignored project data.

Downloads only CPU files from the vendor ZIP using HTTP ranges. Each entry's
length and CRC are checked; paths are confined to the runtime directory.
GPU libraries are omitted for this local CPU deployment.
"""
import io
import struct
import zipfile
import zlib
from pathlib import Path
import httpx

VERSION = '0.40.2'
URL = f'https://github.com/ollama/ollama/releases/download/v{VERSION}/ollama-windows-amd64.zip'
DESTINATION = Path(__file__).resolve().parent / 'data' / 'ollama-runtime'


def install():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        head = client.head(URL)
        head.raise_for_status()
        total = int(head.headers['content-length'])

        def fetch(start, size):
            if size <= 0:
                return b''
            with client.stream('GET', URL, headers={'Range': f'bytes={start}-{start + size - 1}'}) as response:
                if response.status_code != 206:
                    raise RuntimeError('Vendor server must support ranged ZIP downloads')
                data = response.read()
            if len(data) != size:
                raise RuntimeError('Incomplete vendor download')
            return data

        class Remote(io.RawIOBase):
            def __init__(self):
                self.position = 0

            def seekable(self):
                return True

            def seek(self, offset, whence=0):
                self.position = offset if whence == 0 else (self.position + offset if whence == 1 else total + offset)
                return self.position

            def tell(self):
                return self.position

            def read(self, size=-1):
                size = min(size if size >= 0 else total - self.position, total - self.position)
                result = fetch(self.position, size)
                self.position += len(result)
                return result

        with zipfile.ZipFile(Remote()) as archive:
            selected = [item for item in archive.infolist() if not item.is_dir() and not any(
                name in item.filename.lower() for name in ['cuda', 'rocm', 'vulkan', 'cublas', 'cudart', 'nvidia', 'hipblas'])]
            if sum(item.file_size for item in selected) > 200 * 1024 * 1024:
                raise RuntimeError('Unexpected CPU package size; inspect vendor archive')
            for item in selected:
                target = (DESTINATION / item.filename).resolve()
                if not target.is_relative_to(DESTINATION.resolve()):
                    raise RuntimeError('Archive path escaped runtime directory')
                if target.exists() and target.stat().st_size == item.file_size:
                    if zlib.crc32(target.read_bytes()) & 0xffffffff == item.CRC:
                        continue
                header = fetch(item.header_offset, 30)
                if header[:4] != b'PK\x03\x04':
                    raise RuntimeError('Invalid ZIP entry')
                filename_length, extra_length = struct.unpack_from('<HH', header, 26)
                compressed = fetch(item.header_offset + 30 + filename_length + extra_length, item.compress_size)
                content = zlib.decompress(compressed, -15) if item.compress_type == zipfile.ZIP_DEFLATED else compressed
                if len(content) != item.file_size or zlib.crc32(content) & 0xffffffff != item.CRC:
                    raise RuntimeError('Vendor file integrity check failed')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                print('Installed', item.filename, flush=True)
    print('Official CPU runtime ready:', DESTINATION / 'ollama.exe')


if __name__ == '__main__':
    install()
