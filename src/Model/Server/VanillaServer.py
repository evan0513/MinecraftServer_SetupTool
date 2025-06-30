import os
import json
import subprocess
import queue
import threading

from .BaseServer import BaseServer

class VanillaServer(BaseServer):
    name = 'Vanilla'
    version = 'None'
    _running = False

    def __init__(self, path, callback_log):
        self.path = path
        with open(os.path.join(path, "config.json"), 'r') as file:
            self.server_config = json.loads(file.read())
        self.version = self.server_config['server.version']

        self.java_path = os.path.join(path, 'java', 'bin', 'java.exe')
        self.jar_path = os.path.join(path, f'{self.name}-{self.version}.jar')
        self.java_xmx = '4G'
        self.java_xms = '1G'

        self.process = None
        self.log_thread = None
        self.log_queue = queue.Queue()
        self.callback_log = callback_log  # 一個可呼叫的函式，用來即時傳 log 到 UI
        self._running = False


    def set_eula(self, able):
        self.server_config['eula'] = able
        with open(os.path.join(self.path, "config.json"), 'w') as file:
            file.write(json.dumps(self.server_config))

    def get_eula_status(self) -> bool:
        """
        檢查Server的EULA狀態
        """
        return self.server_config.get('eula', False)
    
    def start(self):
        if self.is_running():
            return
        cmd = [
            self.java_path,
            f"-Xms{self.java_xms}",
            f"-Xmx{self.java_xmx}",
            "-jar",
            self.jar_path,
            "nogui"
        ]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=self.path
        )
        self._running = True
        self.log_thread = threading.Thread(target=self._read_log, daemon=True)
        self.log_thread.start()

    def _read_log(self):
        while True:
            if self.process.poll() is not None:
                # process 結束
                self._running = False
                break
            line = self.process.stdout.readline()
            if line:
                if self.callback_log:
                    self.callback_log(line)
                else:
                    print(line, end="")
        # 通知 UI 已經完全停止
        if self.callback_log:
            self.callback_log("[Server 已停止]\n")

    def send_command(self, command):
        if not self.is_running():
            return "伺服器未啟動"
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        return None

    def stop(self):
        if not self.is_running():
            return
        # 使用 stop 指令
        self.send_command("stop")
        # 等待伺服器完全結束
        self.process.wait()
        self._running = False

    def is_running(self):
        return self.process is not None and self.process.poll() is None