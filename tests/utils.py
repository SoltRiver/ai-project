import time
import socket

def wait_for_server(port: int, timeout: int = 30) -> bool:
    """
    指定されたポートでサーバーが起動するのを待機します。
    
    Args:
        port (int): 接続を確認するローカルホストのポート番号。
        timeout (int): タイムアウトまでの秒数 (デフォルト: 30秒)。

    Returns:
        bool: 接続に成功した場合は True、タイムアウトした場合は False。
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)
    return False
