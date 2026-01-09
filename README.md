# 위키독스 블로그 AI 자동 포스팅 🤖

Claude AI를 활용하여 시를 자동으로 생성하고, AI 이미지와 함께 위키독스 블로그에 자동으로 포스팅하는 Python 프로젝트입니다.

## ✨ 주요 기능

- **AI 시 생성**: Claude Opus 4.5를 사용하여 주제에 맞는 창의적인 시 자동 생성
- **AI 이미지 생성**: Freepik API를 통해 시의 내용에 어울리는 썸네일 이미지 자동 생성
- **자동 블로그 포스팅**: 위키독스 블로그에 생성된 시와 이미지를 자동으로 업로드
- **LangGraph 워크플로우**: 복잡한 프로세스를 체계적으로 관리하는 상태 기반 워크플로우

## 📋 요구사항

- Python 3.12 이상 (Python 3.14 사용 시 경고가 발생할 수 있지만 실행에는 문제없습니다)
- 다음 API 키가 필요합니다:
  - [Anthropic API 키](https://console.anthropic.com/) (Claude AI)
  - [위키독스 API 키](https://wikidocs.net/178030)
  - [Freepik API 키](https://www.freepik.com/api)

## 🚀 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/pahkey/wikidocs_blog_ai.git
cd wikidocs_blog_ai
```

### 2. 의존성 설치

**uv 사용 (권장):**
```bash
uv sync
```

**pip 사용:**
```bash
pip install -r requirements.txt
```

또는 직접 설치:
```bash
pip install langgraph langchain langchain-anthropic langchain-community httpx python-dotenv
```

### 3. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성합니다:

```bash
cp .env.example .env
```

그리고 `.env` 파일을 열어 각 API 키를 입력합니다:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
WIKIDOCS_API_KEY=your_wikidocs_api_key_here
FREEPIK_API_KEY=your_freepik_api_key_here
```

## 🔑 API 키 발급 방법

### 1. Anthropic API 키
1. [Anthropic Console](https://console.anthropic.com/)에 접속
2. 회원가입 또는 로그인
3. API Keys 메뉴에서 새 키 생성
4. 생성된 키를 `.env` 파일의 `ANTHROPIC_API_KEY`에 입력

### 2. 위키독스 API 키
1. [위키독스](https://wikidocs.net/)에 로그인
2. [마이페이지](https://wikidocs.net/profile/edit/token)로 이동
3. API 토큰 생성
4. 생성된 토큰을 `.env` 파일의 `WIKIDOCS_API_KEY`에 입력

### 3. Freepik API 키
1. [Freepik API](https://www.freepik.com/api)에 접속
2. 계정 생성 및 API 신청
3. 승인 후 API 키 확인
4. 생성된 키를 `.env` 파일의 `FREEPIK_API_KEY`에 입력

## 💻 사용 방법

### 기본 실행

```bash
# uv 사용
uv run python main.py

# 또는 일반 Python 실행
python main.py
```

### 커스터마이징

`main.py` 파일의 하단에서 주제와 내용을 수정할 수 있습니다:

```python
if __name__ == "__main__":
    result = run_blog_posting(
        topic="봄날의 산책",  # 원하는 주제로 변경
        contents="따뜻한 봄 햇살 아래 공원을 걷는 평화로운 순간"  # 내용 변경
    )
```

## 📂 프로젝트 구조

```
wikidocs_blog_ai/
├── main.py              # 메인 실행 파일
├── .env                 # 환경변수 설정 (gitignore)
├── .env.example         # 환경변수 예시 파일
├── pyproject.toml       # 프로젝트 의존성 정의
├── uv.lock              # uv 패키지 잠금 파일
└── README.md            # 프로젝트 문서
```

## 🔄 워크플로우 설명

1. **시 생성**: Claude AI가 주제와 내용을 바탕으로 시를 작성
2. **블로그 생성**: 위키독스에 빈 블로그 포스트 생성
3. **이미지 생성 요청**: Freepik API에 썸네일 이미지 생성 요청
4. **이미지 상태 확인**: 이미지 생성이 완료될 때까지 폴링
5. **이미지 다운로드 및 업로드**: 생성된 이미지를 다운로드하여 위키독스에 업로드
6. **블로그 업데이트**: 시와 이미지를 포함한 최종 블로그 포스트 완성

## ⚙️ 설정 옵션

`main.py`의 `Config` 클래스에서 다양한 옵션을 조정할 수 있습니다:

```python
@dataclass
class Config:
    max_poll_attempts: int = 30  # 이미지 생성 최대 시도 횟수
    poll_interval: int = 2       # 폴링 간격 (초)
```

## ⚠️ 주의사항

- Python 3.14 사용 시 Pydantic 관련 경고가 나타날 수 있지만, 실행에는 문제가 없습니다
- API 키는 절대 GitHub에 업로드하지 마세요 (`.env` 파일은 `.gitignore`에 포함되어 있습니다)
- Freepik API와 Anthropic API는 사용량에 따라 과금될 수 있으니 주의하세요
- 생성된 블로그는 기본적으로 비공개(`is_public: False`)로 설정됩니다

## 🐛 문제 해결

### "ModuleNotFoundError" 발생 시
```bash
uv sync  # 또는 pip install -r requirements.txt
```

### API 키 관련 오류 발생 시
- `.env` 파일이 올바른 위치에 있는지 확인
- API 키가 정확히 입력되었는지 확인
- API 키에 불필요한 공백이 없는지 확인

### 이미지 생성 타임아웃 발생 시
`max_poll_attempts` 값을 늘려보세요 (기본값: 30)

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

이슈와 풀 리퀘스트는 언제나 환영합니다!

## 📧 문의

문제가 있거나 제안사항이 있다면 [GitHub Issues](https://github.com/pahkey/wikidocs_blog_ai/issues)를 통해 알려주세요.

---

**Made with ❤️ using Claude AI and LangGraph**
