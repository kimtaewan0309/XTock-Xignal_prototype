- 금융 관련 트윗을 확인 후 관련 기업을 매칭하는 모델 개발
- 1차로 AI 모델을 통해 가장 유사한 기업의 티커와 기업명을 get
- 2차로 wikipedia의 S&P500에 속하는 기업들의 내용을 SBERT와 KEYBERT를 통한 벡터화, 핵심 단어 추출 후 트윗과 유사도 계산
- 최종적으로 유사도 점수가 가장 높은 기업 top 3개 return
* 추후 개발할 부분
1. 특정 기업의 트윗이 아닌 미장 전반적인 내용의 트윗 처리 -> SPYM/QQQ와 같은 ETF 활용
2. 정확도 개선 부분 -> AI를 사용하지 않았을 경우 wikipedia의 내용이 최신 정보를 포함하지 않기 때문에 정확도 감소
3. 추가적인 재무 재표 활용 -> 어느 정도 비율로 가중치를 둬서 정확도를 올릴건지


**파일 실행 방법**
- Docker Container를 활용해서 필요 라이브러리를 추가적인 설치 없이 진행
- 최상단 폴더에 .env 파일을 만들고 파일 내에
GOOGLE_API_KEY=(본인의 GOOGLE_API_KEY value)를 넣고 저장
- Docker Container를 설치한 후 VScode를 통해 폴더를 열고 터미널에 "docker-compose up -d --build"를 입력
- 빌드가 완료되고 나서 data_pipeline 폴더 내에 있는 crawling.py -> pipeline.py 순으로 코드를 실행 (실행 코드는 "docker exec -it xtock-pipeline python (code_file_name).py)
이때 sp500_full_wiki.jsonl 파일이 생성된 후에 pipeline.py 코드를 실행하면 sp500_sbert_input.jsonl 파일이 생성
- 파일이 모두 생성됐으면 파일이 제대로 생성됐는지 확인 후 build_vector.py 코드를 실행 (실행 코드는 "docker exec -it xtock-pipeline python build_vector.py)
- backend 폴더에 chroma_db 폴더가 생성된 것을 확인 후에 test_hybrid_search.py 코드를 실행하면 test tweet을 기반으로 유사도가 높은 top3 기업을 출력(실행 코드는 "docker exec -it xtock-backend python test_hybrid_search.py)


- 벤치 마크 모델을 추가
  - SBERT 모델 중 MiniLM 모델과 BGE-M3 모델의 성능을 비교
  - Ai Studio를 활용해서 AI의 도움을 받을 경우와 받지 않을 경우의 성능을 비교
  - AI만 사용했을 때의 모델도 추가하여 섣능을 비교
  - * AI의 temperature를 0.0으로 설정하여 항상 같은 결과값이 나오도록 고정, 프롬프트는 동일하게 사용
  - 최초 성능은 SBERT 모델과 제미나이를 합친 모델의 성능이 가장 우수한 것으로 확인
  - 벤치마크를 위한 트윗의 난이도를 점점 올려가면서 시도한 결과 가장 성능이 우수한 모델은 BGE 모델과 제미나이를 합친 모델의 성능이 가장 우수한 것으로 확인
  - <img width="445" height="208" alt="image" src="https://github.com/user-attachments/assets/454d1a9a-3a93-4dd9-91a5-7873882c9a9d" />


# 12/10일자 업데이트

- 선준님이 개발한 모델 + 제가 개발한 모델을 통합하여 최종 모델을 생성
## **파일 실행 방법**
- 위와 마찬가지로 Docker Container를 사용해서 코드를 실행
### 1. 컨테이너 빌드 및 실행
- model_prototype 폴더로 이동한 다음
  ```docker-compose up -d --build```
  를 통해 도커를 시작
### 2. 데이터 수집
- 빌드가 완료된 후
  1. S&P 500 기업 리스트 최신화
    ```
    docker exec -it xtock-pipeline python data_pipeline/update_sp500_list.py 
    ```
  2. 위피키디아 데이터 수집 및 키워드 추출
    ```
    docker exec -it xtock-pipeline python data_pipeline/pipeline.py
    ```
  3. 최신 재무지표 수집
    ```
    docker exec -it xtock-pipeline python data_pipeline/fetch_financial_metrics.py
    ```
- 데이터 파일이 깃허브에 없기 때문에 새롭게 생성해야되는데 시간이 오래 소요됨
- 따라서 데이터 파일을 따로 빼서 관리 (google drive)
### 3. 벡터 DB 구축
- 수집된 데이터를 바탕으로 검색에 사용될 ChromaDB (Static + Dynamic)을 구축
  ```
  docker exec -it xtock-pipeline python data_pipeline/build_dual_db.py
  ```
- 마찬가지로 ChromaDB 파일의 크기가 크기 때문에 google drive를 통해 따로 관리
### 4. 모델 학습 (Hyperparameter Tuning)
- 검색 정확도를 높이기 위해 Optuna를 사용하여 최적의 가중치를 찾음
- 학습 결과는 backend/best_params.json에 저장 (google drive를 통해 관리)
  ```
  docker exec -it xtock-pipeline python backend/train_model.py
  ```
### 5. 검색 API 서버 실행
- FastAPI 서버를 실행하여 외부에서 검색 요청을 받을 수 있도록 함
  ```
  docker exec -it xtock-pipeline uvicorn backend.search_service:app --host 0.0.0.0 --port 8000 --reload
  ```
## API 테스트 하는 방법
- url: http://localhost:8001/docs
- 해당 url을 통해서 query를 전송할 수 있도 response 확인 가능
