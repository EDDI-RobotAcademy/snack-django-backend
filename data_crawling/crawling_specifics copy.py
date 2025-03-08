from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import csv
import requests
from datetime import datetime

# 크롬 드라이버 설정
service = Service("/opt/homebrew/bin/chromedriver")
options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# 카카오 주소 검색 API 키 (필수 입력)
KAKAO_API_KEY = '6d9dc3df95f90cbe474e8b518e13f2f2'

# 서울시 구 리스트
seoul_gu_list = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구",
    "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"
]

# 좌표 변환 함수
def get_lat_lon(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json().get('documents', [])
        if result:
            return result[0]['y'], result[0]['x']
    return None, None

# 크롬 드라이버 초기화
def init_driver():
    driver = webdriver.Chrome(service=service, options=options)
    driver.get('https://map.kakao.com/')
    time.sleep(2)
    return driver

# 검색어 입력 및 검색 실행
def search_keyword(driver, keyword):
    search_area = driver.find_element(By.ID, 'search.keyword.query')
    search_area.clear()
    search_area.send_keys(keyword)
    search_area.send_keys(Keys.ENTER)
    time.sleep(3)

    remove_dimmed_layer(driver)
    click_place_tab(driver)
    click_place_more(driver)

# 팝업 제거
def remove_dimmed_layer(driver):
    try:
        dimmed_layer = driver.find_element(By.ID, 'dimmedLayer')
        driver.execute_script("arguments[0].style.display='none';", dimmed_layer)
    except:
        pass

# 장소 탭 클릭
def click_place_tab(driver):
    driver.find_element(By.XPATH, '//*[@id="info.main.options"]/li[2]/a').click()
    time.sleep(2)

# 장소 더보기 클릭
def click_place_more(driver):
    try:
        driver.find_element(By.ID, 'info.search.place.more').click()
        time.sleep(2)
    except:
        pass

# 메뉴 탭 펼치고 메뉴 수집
def expand_menu_tab_and_collect(driver):
    menu_items = []
    try:
        menu_tab = driver.find_element(By.CSS_SELECTOR, 'a[href="#menuInfo"]')
        menu_tab.click()
        time.sleep(2)

        while True:
            try:
                more_button = driver.find_element(By.CSS_SELECTOR, '.wrap_more a.link_more')
                if more_button.is_displayed():
                    more_button.click()
                    time.sleep(2)
                else:
                    break
            except:
                break

        menu_elements = driver.find_elements(By.CSS_SELECTOR, '.list_goods > li')
        for element in menu_elements:
            name = element.find_element(By.CSS_SELECTOR, '.tit_item').text.strip()
            try:
                price = element.find_element(By.CSS_SELECTOR, '.desc_item').text.strip()
            except:
                price = '가격정보 없음'
            menu_items.append(f'{name} ({price})')

    except Exception as e:
        print(f"❌ 메뉴 수집 실패: {e}")
        return ['메뉴 없음']

    return menu_items if menu_items else ['메뉴 없음']

# 매장 상세 정보 수집
def get_store_details(driver, detail_url):
    original_window = driver.current_window_handle

    driver.execute_script("window.open(arguments[0]);", detail_url)
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)

    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(2)

    menu_list = expand_menu_tab_and_collect(driver)
    menu_text = ', '.join(menu_list)

    driver.close()
    driver.switch_to.window(original_window)

    return menu_text

# 모든 페이지 크롤링
def crawl_all_pages(driver):
    all_data = []

    def process_current_page():
        nonlocal all_data
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        stores = soup.select('.placelist > .PlaceItem')

        for store in stores:
            try:
                name = store.select_one('.head_item .tit_name .link_name').text.strip()
                degree = store.select_one('.rating .score .num').text.strip()
                review_count = store.select_one('.review em[data-id="numberofreview"]').text.strip() or '0'
                address = store.select_one('.info_item .addr').text.strip()
                tel = store.select_one('.info_item .phone').text.strip() if store.select_one('.info_item .phone') else '전화번호 없음'
                detail_url = store.select_one('.contact .moreview')['href']

                menu_text = get_store_details(driver, detail_url)

                print(f"📍 {name} | 평점: {degree} | 리뷰 {review_count}개 수집 완료")
                all_data.append([name, degree, review_count, address, tel, menu_text])

            except Exception as e:
                print(f"❌ 매장 크롤링 실패: {e}")

    while True:
        process_current_page()

        try:
            next_button = driver.find_element(By.ID, 'info.search.page.next')
            if "disabled" in next_button.get_attribute("class"):
                print("✅ 마지막 페이지 도달, 크롤링 종료")
                break
            next_button.click()
            time.sleep(2)
        except:
            print("❌ 다음 버튼 클릭 실패, 크롤링 종료")
            break

    return all_data

# CSV 저장 (날짜 포함 & 위도/경도 추가)
def save_to_csv(gu_name, data):
    today = datetime.now().strftime("%Y%m%d")
    filename = f'{today}_{gu_name}_맛집_크롤링.csv'

    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['이름', '평점', '리뷰수', '주소', '위도', '경도', '전화번호', '메뉴'])

        for row in data:
            name, degree, review_count, address, tel, menu_text = row
            lat, lon = get_lat_lon(address)
            writer.writerow([name, degree, review_count, address, lat, lon, tel, menu_text])

    print(f"✅ {gu_name} 저장 완료 ({filename})")

# 서울시 구별 크롤링 실행
def crawl_seoul_gu():
    for gu in seoul_gu_list:
        print(f"🔹 {gu} 크롤링 시작!")
        driver = init_driver()
        search_keyword(driver, f'{gu} 맛집')

        all_data = crawl_all_pages(driver)
        save_to_csv(gu, all_data)

        driver.quit()
        print(f"✅ {gu} 크롤링 및 저장 완료\n")

# 메인 실행
if __name__ == '__main__':
    crawl_seoul_gu()
