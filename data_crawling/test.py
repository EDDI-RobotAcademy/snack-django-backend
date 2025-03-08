import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 크롬 드라이버 경로
CHROME_DRIVER_PATH = "/path/to/your/chromedriver"  # 본인 환경에 맞게 수정

# WebDriver 옵션 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")  # 필요시 headless 모드
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

# 페이지 로드 대기 함수
def wait_for_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except:
        return None

# 안전한 텍스트 추출 함수
def safe_get_text(element):
    return element.text.strip() if element else ""

# 매장 상세 정보 크롤링 함수
def crawl_store_info(store_url):
    driver.get(store_url)
    time.sleep(2)

    if not driver.current_url.startswith("https://place.map.kakao.com/"):
        print(f"❌ 잘못된 상세페이지: {driver.current_url}")
        return None

    store_name_element = wait_for_element(driver, By.CSS_SELECTOR, "h3.tit_place", timeout=5)
    if store_name_element is None:
        print(f"❌ 상세페이지 로드 실패: {store_url}")
        return None

    store_info = {
        "상호명": safe_get_text(store_name_element),
        "카테고리": safe_get_text(driver.find_element(By.CSS_SELECTOR, ".info_cate")),
        "주소": safe_get_text(driver.find_element(By.CSS_SELECTOR, ".txt_detail")),
        "전화번호": safe_get_text(driver.find_element(By.CSS_SELECTOR, ".info_suggest .txt_detail")),
        "별점": safe_get_text(driver.find_element(By.CSS_SELECTOR, ".num_star")),
        "리뷰수": safe_get_text(driver.find_element(By.CSS_SELECTOR, ".link_review .info_num")),
        "영업시간": safe_get_text(driver.find_element(By.CSS_SELECTOR, ".info_runtime")),
        "휴무일": "",  # 필요시 추가 크롤링 가능
        "위도": driver.execute_script("return mapview.map.getCenter().getLat();"),
        "경도": driver.execute_script("return mapview.map.getCenter().getLng();")
    }

    # 메뉴 크롤링
    store_info["메뉴"] = []
    try:
        menu_elements = driver.find_elements(By.CSS_SELECTOR, ".list_goods .info_goods")
        for menu in menu_elements:
            name = safe_get_text(menu.find_element(By.CSS_SELECTOR, ".tit_item"))
            price = safe_get_text(menu.find_element(By.CSS_SELECTOR, ".desc_item"))
            store_info["메뉴"].append({"메뉴명": name, "가격": price})
    except:
        pass

    return store_info

# 구별 장소 목록 수집 함수
def get_places_by_district(district):
    search_url = f"https://map.kakao.com/?q={district}+맛집"
    driver.get(search_url)
    time.sleep(2)

    place_links = []
    for _ in range(3):  # 첫 3페이지 탐색
        places = driver.find_elements(By.CSS_SELECTOR, ".link_name")
        place_links.extend([p.get_attribute("href") for p in places])
        
        next_btn = driver.find_element(By.CSS_SELECTOR, ".btn_next")
        if "off" in next_btn.get_attribute("class"):
            break
        next_btn.click()
        time.sleep(2)

    return place_links

# 서울시 전체 구 리스트
seoul_districts = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구",
    "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구",
    "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구",
    "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"
]

# 최종 실행 함수
def main():
    all_data = []
    for district in seoul_districts:
        print(f"📍 {district} 맛집 크롤링 시작...")
        place_urls = get_places_by_district(district)

        for url in place_urls:
            info = crawl_store_info(url)
            if info:
                info["구"] = district
                all_data.append(info)

    df = pd.DataFrame(all_data)
    df.to_excel("서울_맛집_정보_크롤링_결과.xlsx", index=False)
    print("✅ 크롤링 완료 및 저장 완료")

if __name__ == "__main__":
    main()
    driver.quit()
