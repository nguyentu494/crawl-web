import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from io import BytesIO

BASE_URL = "https://masothue.com"

PROVINCES = {
    "Hà Nội": ("ha-noi", 1),
    "TP Hồ Chí Minh": ("tp-ho-chi-minh", 79),
    "Đà Nẵng": ("da-nang", 48),
    "Cà Mau": ("ca-mau", 108),
    "Bình Dương": ("binh-duong", 74),
    "Bắc Ninh": ("bac-ninh", 27),
}

def parse_company_detail(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return {"Tên công ty": f"Lỗi khi truy cập {url}: {e}"}

    soup = BeautifulSoup(r.text, "html.parser")
    name = soup.select_one("h1")
    name = name.text.strip() if name else ""

    info = {}
    rows = soup.select("table.table-taxinfo tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            key = cols[0].text.strip()
            if "Điện thoại" in key:
                span = cols[1].select_one("span.copy")
                val = span.text.strip() if span else cols[1].get_text(strip=True)
            else:
                val = cols[1].get_text(strip=True)
            info[key] = val

    return {
        "Tên công ty": name,
        "Mã số thuế": info.get("Mã số thuế", ""),
        "Người đại diện": info.get("Người đại diện", ""),
        "Địa chỉ": info.get("Địa chỉ", ""),
        "Điện thoại": info.get("Điện thoại", ""),
        "Ngày hoạt động": info.get("Ngày hoạt động", ""),
    }

def crawl_page(url, headers, delay=1, progress=None, status=None, current=0):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        st.error(f"Lỗi khi request {url}: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select(".tax-listing h3 a")
    if not rows:
        return []

    all_data = []
    for idx, a in enumerate(rows, 1):
        detail_url = BASE_URL + a["href"]
        data = parse_company_detail(detail_url, headers)
        all_data.append(data)

        if progress:
            done = current + idx
            progress.progress(min(done / len(rows), 1.0))
            if status:
                status.text(f"🔎 Đang crawl {done}/{len(rows)} công ty...")

        time.sleep(delay)
    return all_data

def get_total_pages(url, headers):
    """Lấy tổng số trang từ HTML (nếu có phân trang)."""
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    pages = soup.select(".pagination li a")
    nums = []
    for p in pages:
        try:
            nums.append(int(p.text.strip()))
        except:
            pass
    return max(nums) if nums else None


def get_data_from_url(url, max_pages=None, delay=1, progress=None, status=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi,en-US;q=0.7,en;q=0.3",
        "Connection": "keep-alive",
        "Referer": "https://masothue.com/",
        "Upgrade-Insecure-Requests": "1",
    }
    all_data, page = [], 1

    # Tính tổng số trang nếu có thể
    while True:
        crawl_url = f"{url}?page={page}"
        data = crawl_page(
            crawl_url,
            headers,
            delay,
            progress,
            status,
            current=len(all_data),
        )
        if not data:
            break
        all_data.extend(data)

        if max_pages and page >= max_pages:
            break
        page += 1
    return all_data

def get_data_from_province(slug, pid, max_pages=None, delay=1, progress=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi,en-US;q=0.7,en;q=0.3",
        "Connection": "keep-alive",
        "Referer": "https://masothue.com/",
        "Upgrade-Insecure-Requests": "1",
    }
    all_data, page = [], 1
    base_url = f"{BASE_URL}/tra-cuu-ma-so-thue-theo-tinh/{slug}-{pid}"

    while True:
        crawl_url = f"{base_url}?page={page}"
        data = crawl_page(crawl_url, headers, delay, progress, len(all_data), 1000)
        if not data:
            break
        all_data.extend(data)
        if max_pages and page >= max_pages:
            break
        page += 1
    return all_data

# ================== STREAMLIT APP ==================
st.title("🕷️ Cào dữ liệu doanh nghiệp từ masothue.com")

mode = st.radio("Chọn cách crawl:", ["Theo URL", "Theo khu vực"])
max_pages = st.number_input("Số trang tối đa (0 = crawl hết)", min_value=0, value=1, step=1)

url = None
province = None
if mode == "Theo URL":
    url = st.text_input("Nhập URL đầy đủ (ví dụ: https://masothue.com/tra-cuu-ma-so-thue-theo-tinh/ca-mau-108)")
elif mode == "Theo khu vực":
    province = st.selectbox("Chọn tỉnh/thành", list(PROVINCES.keys()))

if st.button("🚀 Bắt đầu cào dữ liệu"):
    progress = st.progress(0)
    status = st.empty()   # placeholder cho text trạng thái
    st.info("Đang tiến hành crawl, vui lòng chờ...")

    if mode == "Theo URL" and url:
        data = get_data_from_url(url, max_pages if max_pages > 0 else None, progress=progress, status=status)
    elif mode == "Theo khu vực" and province:
        slug, pid = PROVINCES[province]
        data = get_data_from_province(slug, pid, max_pages if max_pages > 0 else None, progress=progress, status=status)
    else:
        data = []

    if not data:
        st.error("Không tìm thấy dữ liệu!")
    else:
        df = pd.DataFrame(data)
        st.success(f"✅ Đã crawl được {len(df)} dòng.")
        st.dataframe(df, use_container_width=True)

        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("📥 Tải Excel", output.getvalue(), "ket_qua.xlsx")
