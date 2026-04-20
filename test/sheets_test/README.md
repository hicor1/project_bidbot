# 구글시트 수동 테스트

## 사전 준비
1. `pip install gspread google-auth` (한 번)
2. 프로젝트 루트 `.env` 에 아래 추가:
   ```
   GOOGLE_CREDENTIALS_PATH=...\docs\secret\project-bitbot-XXXXX.json
   GOOGLE_SHEET_ID=1hZvBPhWc42xZtVRX-tlgxd8Q46UsOpfOZBbPsHX-f_I
   GOOGLE_SHEET_WORKSHEET=상품마스터
   ```
3. 시트에 서비스 계정 이메일 `편집자` 공유 완료 필요

## 파일

| 파일 | 안전? | 동작 |
|------|------|------|
| `01_read.py` | ✅ 읽기 전용 | 시트 접속 + 헤더 검증 + 전체 행 덤프 |

## 실행
Spyder 에서 `runfile()` 로 실행하거나:

```cmd
cd /d "e:\2. hicor\Python\project_bidbot"
C:\Users\hicor\miniconda3\envs\spyder\python.exe -X utf8 test\sheets_test\01_read.py
```
