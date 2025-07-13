import requests
from bs4 import BeautifulSoup
import re

class fabric_server:
    def __init__(self,path):
        # self.__mc_version = mc_version
        self.__path = path
        pass


    def grep_mc_version(self,stable_only) -> list[str]:
        # Go check the home page of forge downloader
        r = requests.get("https://meta.fabricmc.net/v2/versions/game")
        js = r.json()
        iter = map(lambda v:v["version"] if stable_only==v["stable"] or not stable_only else None,js)
        return [i for i in iter if i!=None]

    
    def grep_loader_version(self,stable_only) -> list[str]:
        r = requests.get(f"https://meta.fabricmc.net/v2/versions/loader")
        js = r.json()
        iter = map(lambda v:v["version"] if (stable_only==v["stable"] or not stable_only) and v["separator"]=="." else None,js)
        return [i for i in iter if i!=None]
    
    
    def grep_installer_version(self,stable_only) -> list[str]:
        r = requests.get(f"https://meta.fabricmc.net/v2/versions/installer")
        js = r.json()
        iter = map(lambda v:v["version"] if stable_only==v["stable"] or not stable_only else None,js)
        return [i for i in iter if i!=None]
    
    
    def download_server(self,mc_ver,loader_ver,install_ver) -> None:
        response = requests.get(f"https://meta.fabricmc.net/v2/versions/loader/{mc_ver}/{loader_ver}/{install_ver}/server/jar", stream=True)
        with open(f"{self.__path}/server.jar", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        pass

def main():
    fs = fabric_server("./")
    print()
    print(fs.grep_loader_version(False))
    print(fs.grep_installer_version(True))
    fs.download_server(fs.grep_mc_version(True)[0],fs.grep_loader_version(False)[0],fs.grep_installer_version(True)[0])
    


if __name__ == "__main__":
    main()