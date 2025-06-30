import os
import json

class Config:
    def __init__(self, app_name='ServerLuncher'):
        if os.name == 'nt':
            base = os.getenv('LOCALAPPDATA')
        else:
            base = os.path.expanduser('~/.local/share')
        self.app_folder = os.path.join(base, app_name)
        os.makedirs(self.app_folder, exist_ok=True)
        self.config_file = os.path.join(self.app_folder, 'config.json')
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def get_and_save(self, key, default):
        value = self.config.get(key, None)
        if value is None:
            self.set(key, default)
        return default


    def get_config_path(self):
        return self.config_file

    def get_app_folder(self):
        return self.app_folder

# 使用範例
if __name__ == "__main__":
    cfg = Config()

    print("伺服器目錄:", cfg.get('server_dir'))
    print("設定檔路徑:", cfg.get_config_path())
    print("應用程式資料夾:", cfg.get_app_folder())
