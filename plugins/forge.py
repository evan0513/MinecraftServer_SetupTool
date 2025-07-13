import requests
from bs4 import BeautifulSoup
import re

class forge_server:
    def __init__(self,path):
        self.__path = path
        pass


    def grep_mc_version(self) -> list[str]:
        # Go check the home page of forge downloader
        r = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/")
        soup = BeautifulSoup(r.text,features="html.parser")
        return list(map(lambda v: v.text,soup.select("ul .nav-collapsible li a")))


    def grep_forge_version(self,mc_ver) -> list[str]:
        r2 = requests.get(f"https://files.minecraftforge.net/net/minecraftforge/forge/index_{mc_ver}.html",timeout=30)
        r2.encoding = "utf-8"
        soup = BeautifulSoup(r2.text,features="html.parser")
        return list(map(lambda v: str(v.text).strip(),soup.find_all(class_="download-version")))
    
    def download_installer(self,mc_ver,f_ver) -> None:
        response = requests.get(f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_ver}-{f_ver}/forge-{mc_ver}-{f_ver}-installer.jar", stream=True)
        with open(f"{self.__path}/installer.jar", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        pass

def main():
    fs = forge_server("./")
    mc_vers = fs.grep_mc_version()
    forge_versions = fs.grep_forge_version(mc_vers[0]) # 0 for the latest
    fs.download_installer(mc_vers[0],forge_versions[0]) # 0 for the latest
    


if __name__ == "__main__":
    main()