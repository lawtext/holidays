"""
政府页面正文抽取
"""

import json
import re
import sys
import time
from pathlib import Path

import httpx
from lxml import etree, html
from markdownify import markdownify as md

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
    )
}
DATA_FILE = "data.json"
SAVE_DIR = "docs"


def parse_page_to_md(text: str) -> str:
    tree = html.fromstring(text)
    # 尝试匹配正文容器
    selectors = [
        '//*[@id="UCAP-CONTENT"]',
        '//*[contains(@class, "pages_content")]',
        '//*[contains(@class, "article-content")]',
        '//*[contains(@class, "TRS_Editor")]',
        "//article",
    ]
    for xpath in selectors:
        nodes = tree.xpath(xpath)
        if nodes:
            md_content = md(etree.tostring(nodes[0]))
            break

    md_content = md_content.replace(")", "）").replace("(", "（").replace("○", "〇")
    md_content = re.sub(r"^\s*(国务院办公厅关于\d+年)\n+(部分)", r"# \1\2", md_content, flags=re.MULTILINE)
    md_content = re.sub(r"^(国办发明电)", r"> \1", md_content, flags=re.MULTILINE)
    md_content = re.sub(r"^　　(\S)", r"\n\1", md_content, flags=re.MULTILINE)
    md_content = re.sub(r"^\s+|\s+$", "", md_content, flags=re.MULTILINE)
    md_content = re.sub(r"\n{3,}", r"\n\n", md_content)

    return md_content


def process(url: str, output_file: Path, headers: dict[str, str], timeout: int = 30) -> None:
    response = httpx.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    markdown_content = parse_page_to_md(response.text)

    # save
    markdown = "\n".join(["---", f"source: {url}", "---", "", markdown_content.strip(), ""])
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run.py <output> <data.json>")
        sys.exit(1)

    save_dir = sys.argv[1]
    data_file = sys.argv[2]
    if not Path(data_file).exists():
        print(f"No file = {data_file}")
        sys.exit(1)

    print(f"Save to {save_dir}")
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    ignore = 0
    for year, url in data.items():
        save_file = Path(save_dir, f"{year}.md")
        if save_file.exists():
            ignore += 1
            continue
        count += 1
        print(f"Process {year} {url}")
        process(url, save_file, HEADERS)
        time.sleep(2)

    print(f"Done: process = {count}, ignore = {ignore}")
