"""Bounded subprocess execution for optional source backends."""
import os
import signal
import subprocess
import tempfile
import time


class BackendError(ValueError):
    pass


def run_json_command(command, *, timeout=75, max_bytes=2_000_000):
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=output, stderr=errors, stdin=subprocess.DEVNULL,
                                   start_new_session=True)
        started = time.monotonic()
        try:
            while process.poll() is None:
                if time.monotonic() - started > timeout:
                    raise BackendError('backend_timeout')
                if os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > max_bytes:
                    raise BackendError('output_limit')
                time.sleep(.05)
            if os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > max_bytes:
                raise BackendError('output_limit')
            if process.returncode:
                errors.seek(0)
                message = errors.read(8192).decode(errors='replace').lower()
                code = ('browser_bridge_unavailable' if process.returncode == 69 else
                        'login_required' if process.returncode == 77 or 'sign in' in message or 'login' in message else
                        'rate_limited' if '429' in message else 'backend_failed')
                raise BackendError(code)
            output.seek(0)
            return output.read(max_bytes)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
