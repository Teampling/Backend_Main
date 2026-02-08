# Git Convention

---

## 1. 브랜치 전략

### 기본 브랜치
- `main` 브랜치만 사용한다.
- 별도의 `develop` 브랜치는 두지 않는다.


### 브랜치 네이밍 규칙
```text
<type>/<issue-number>-<short-description>
```
### 예시:
```
feat/12-multi-assignee
fix/18-null-error
chore/22-update-lint
```

### type 목록
- feat : 기능 추가
- fix : 버그 수정
- refactor : 구조 개선
- chore : 설정, 빌드, 기타 작업
- docs : 문서
- test : 테스트

### 규칙:
- 이슈 번호는 필수
- 소문자 + 하이픈(-) 사용
- 설명은 3~5단어 이내

---

## 2. 커밋 규칙

### 기본 형식
```text
<type>(<scope>): <subject>
```
- 커밋 메시지는 의미가 드러나도록 작성한다.
- 브랜치 내부 커밋은 자유롭게 작성해도 무방하다.
- scope는 마땅히 없다면 생략 가능하다.

### 예시:
```
feat(work): 작업에 담당자 다중 지정 기능 추가
fix(api): 담당자 미지정 시 400 에러 반환
refactor(service): 작업 생성 로직 분리
docs: readme 작성
```

### type 규칙
- feat : 기능 추가
- fix : 버그 수정
- refactor : 구조 개선
- chore : 설정, 빌드, 기타 작업
- docs : 문서
- test : 테스트

---

## 3. Pull Request 규칙
- PR 제목은 작업 내용을 명확히 드러낸다.
-  하나의 기능/버그 단위를 기준으로 한다.
- 제목은 대표 커밋 메시지를 따른다.

---

## 4. 머지 정책
- 기본 머지 방식은 Squash merge
- 머지 조건은 CI 통과와 리뷰어 1명 승인