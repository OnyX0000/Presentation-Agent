from dotenv import load_dotenv
import urllib.request
import urllib.parse
import os
import json
import pandas as pd
from bs4 import BeautifulSoup
load_dotenv("C:/wanted/Lang/Presentation-Agent/.env")

def naver_developer(search, site, max_results=500):
    """네이버 API를 사용하여 데이터를 검색하고 'title'과 'link'만 Pandas DataFrame으로 반환"""
    
    encText = urllib.parse.quote(search)
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")

    all_results = [] 
    display = 100 
    
    for start in range(1, max_results + 1, display):  
        url = f"https://openapi.naver.com/v1/search/{site}.json?query={encText}&display={display}&start={start}&sort=date"
        print(f"Fetching: {url}")  

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)

        try:
            response = urllib.request.urlopen(request)
            rescode = response.getcode()

            if rescode == 200:
                response_body = response.read()
                response_data = response_body.decode('utf-8')
                response_dict = json.loads(response_data)
                
                items = response_dict.get("items", [])
                
                # title과 link만 저장
                filtered_items = [{"title": item["title"], "link": item["link"]} for item in items]
                all_results.extend(filtered_items)  

                if len(items) < display:  # 마지막 페이지면 종료
                    break
            else:
                print(f"Error Code: {rescode}")
                break

        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code} - {e.reason}")
            break
        except urllib.error.URLError as e:
            print(f"URL Error: {e.reason}")
            break

    # Pandas DataFrame으로 변환
    csv_data = pd.DataFrame(all_results)

    return csv_data

def parsing(df, site):
    """ `BeautifulSoup`을 사용하여 HTML 태그 제거 후 기존 데이터프레임에 반영하고 저장 """

    def clean_html(text):
        """HTML 태그 제거"""
        if pd.isna(text):  # NaN 값이 있는 경우 빈 문자열로 대체
            return ""
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().strip()  # HTML 태그 제거 후 공백 제거

    # 'title'에서 HTML 태그 제거 (link는 HTML 태그 없음)
    df['title'] = df['title'].apply(clean_html)

    # CSV 저장 경로 설정
    save_dir = "../data/csv"
    csv_file_name = f"naver_{site}.csv"
    save_path = os.path.join(save_dir, csv_file_name)

    os.makedirs(save_dir, exist_ok=True)

    df.to_csv(save_path, index=False, encoding="utf-8-sig")

    print(f"데이터가 정제되어 저장되었습니다: {save_path}")
    
    return df 

search_list = ['webkr', 'doc', 'kin', "cafearticle"]

site_dict = {}
for site in search_list:
    df = naver_developer("발표 준비", site)
    df_parsing = parsing(df,site) 

    site_dict[site] = pd.read_csv(f"../data/csv/naver_{site}.csv")