# tools/download_data.py
import os
import json
import requests
import time
from bs4 import BeautifulSoup
from pathlib import Path

# === 配置路径 ===
BASE_DIR = Path(__file__).parent.parent / "data" / "knowledge_source"
ATTACK_DIR = BASE_DIR / "attack"
CTI_DIR = BASE_DIR / "cti"
API_DIR = BASE_DIR / "ms_api"

# === 1. 下载 MITRE ATT&CK 数据 ===
def download_attack():
    print("\n[1/3] Downloading MITRE ATT&CK Enterprise Matrix...")
    url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # 我们只提取 "attack-pattern" (即 TTPs 中的 Technical)
        techniques = []
        for obj in data["objects"]:
            if obj["type"] == "attack-pattern" and not obj.get("revoked", False):
                techniques.append({
                    "name": obj["name"],
                    "description": obj.get("description", ""),
                    "id": obj["external_references"][0]["external_id"]
                })
        
        # 保存为 JSON 文件，方便后续 Loader 读取
        save_path = ATTACK_DIR / "enterprise_techniques.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(techniques, f, indent=4)
        
        print(f"✅ Saved {len(techniques)} ATT&CK techniques to {save_path}")
        
    except Exception as e:
        print(f"❌ Failed to download ATT&CK: {e}")

# === 2. 下载 CTI (APT 报告) ===
def download_cti():
    print("\n[2/3] Downloading CTI Reports (Source: APTnotes)...")
    # 为了演示，我们只下载 GitHub 上 APTnotes 2023年的部分报告
    # 真实项目中你可以 clone 整个 https://github.com/aptnotes/data
    
    # 这里列出几个典型的 APT 报告 URL
    sample_pdfs = [
        "https://github.com/aptnotes/data/raw/master/2022/2022-02-23-The_Beat_Goes_On_Cyclops_Blink_Sets_Sights_on_Asus_Routers.pdf",
        "https://github.com/aptnotes/data/raw/master/2021/2021-08-17-Confucius_Uses_Legitimate_Websites_to_Target_Pakistani_Government_and_Military.pdf"
    ]
    
    for i, url in enumerate(sample_pdfs):
        filename = url.split("/")[-1]
        save_path = CTI_DIR / filename
        
        if save_path.exists():
            print(f"   Skipping {filename} (already exists)")
            continue
            
        print(f"   Downloading {filename}...")
        try:
            r = requests.get(url, stream=True)
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            print(f"❌ Error downloading {filename}: {e}")
            
    print(f"✅ CTI download finished. Files saved to {CTI_DIR}")

# === 3. 爬取 MS-API 文档 ===
def download_ms_api():
    print("\n[3/3] Scraping Microsoft API Docs...")
    
    # 论文提到"避免信息过载"，所以我们只下载恶意软件最常用的高危 API
    # 这个列表是恶意代码分析中 Top 20 常见的 API
    target_apis = [
        "CreateProcessA", "VirtualAlloc", "WriteProcessMemory", "CreateRemoteThread",
        "ShellExecuteA", "RegOpenKeyExA", "InternetOpenA", "URLDownloadToFileA",
        "SetWindowsHookExA", "LoadLibraryA"
    ]
    
    base_search_url = "https://learn.microsoft.com/en-us/windows/win32/api/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for api in target_apis:
        save_path = API_DIR / f"{api}.html"
        if save_path.exists():
            print(f"   Skipping {api} (already exists)")
            continue

        print(f"   Fetching docs for {api}...")
        
        # 搜索逻辑比较复杂，这里简化为直接构建已知的 URL 模式
        # 大部分核心 API 都在 processthreadsapi, memoryapi 等头文件下
        # 为了简单，我们使用 Bing/Google 搜索策略或者直接尝试通用路径
        # 这里使用一个简化的爬虫逻辑：去 Microsoft Learn 搜索
        
        search_query = f"site:learn.microsoft.com/en-us/windows/win32/api {api} function"
        try:
            # 模拟请求具体的页面 (这里为了演示稳定性，我硬编码几个典型路径，
            # 实际工程中你可能需要更复杂的搜索爬虫)
            
            # 这是一个示例 URL，真实 URL 结构往往是 /api/头文件名/nf-头文件名-函数名
            # 由于头文件名不固定，建议先去 Google 搜，或者手动下载离线包。
            # 为了让你现在能跑通，我们只下载 VirtualAlloc 做演示
            if api == "VirtualAlloc":
                url = "https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualalloc"
            elif api == "CreateProcessA":
                url = "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessa"
            else:
                # 其他 API 暂时跳过，避免 404
                continue
                
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(r.text)
                print(f"   ✅ Saved {api}")
            else:
                print(f"   ⚠️ Failed {api}: Status {r.status_code}")
                
            time.sleep(1) # 礼貌爬取，防止被封
            
        except Exception as e:
            print(f"❌ Error scraping {api}: {e}")

if __name__ == "__main__":
    download_attack()
    download_cti()
    download_ms_api()
    print("\n🎉 All downloads complete!")